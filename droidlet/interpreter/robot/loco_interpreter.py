"""
Copyright (c) Facebook, Inc. and its affiliates.
"""

from typing import Tuple, Dict, Any, Optional

from droidlet.memory.memory_nodes import PlayerNode
from droidlet.task.task import ControlBlock, maybe_task_list_to_control_block
from droidlet.interpreter import (
    AGENTPOS,
    ConditionInterpreter,
    get_repeat_num,
    Interpreter,
    AttributeInterpreter,
    interpret_dance_filter,
)

from droidlet.shared_data_structs import ErrorWithResponse
from .spatial_reasoning import ComputeLocations
from .interpret_facing import FacingInterpreter
from .point_target import PointTargetInterpreter

import droidlet.interpreter.robot.dance as dance
import droidlet.interpreter.robot.tasks as tasks


def post_process_loc(loc, interpreter):
    self_mem = interpreter.memory.get_mem_by_id(interpreter.memory.self_memid)
    yaw, _ = self_mem.get_yaw_pitch()
    return (loc[0], loc[2], yaw)


def add_default_locs(interpreter):
    interpreter.default_frame = "AGENT"
    interpreter.default_loc = AGENTPOS


class LocoInterpreter(Interpreter):
    """This class handles processes incoming chats and modifies the task stack.

    Handlers should add/remove/reorder tasks on the stack, but not
    execute them.
    """

    def __init__(self, speaker, logical_form_memid, agent_memory, memid=None, low_level_data=None):
        super().__init__(speaker, logical_form_memid, agent_memory, memid=memid)
        self.default_debug_path = "debug_interpreter.txt"
        self.post_process_loc = post_process_loc
        add_default_locs(self)

        # FIXME!
        self.workspace_memory_prio = []  # noqa

        self.subinterpret["attribute"] = AttributeInterpreter()
        self.subinterpret["condition"] = ConditionInterpreter()
        self.subinterpret["specify_locations"] = ComputeLocations()
        self.subinterpret["facing"] = FacingInterpreter()
        self.subinterpret["dances_filters"] = interpret_dance_filter
        self.subinterpret["point_target"] = PointTargetInterpreter()

        self.action_handlers["DANCE"] = self.handle_dance
        self.action_handlers["GET"] = self.handle_get
        self.action_handlers["DROP"] = self.handle_drop

        self.task_objects = {
            "move": tasks.Move,
            "look": tasks.Look,
            "dance": tasks.Dance,
            "point": tasks.Point,
            "turn": tasks.Turn,
            "autograsp": tasks.AutoGrasp,
            "control": ControlBlock,
            "get": tasks.Get,
            "drop": tasks.Drop,
        }

    def handle_get(self, agent, speaker, d) -> Tuple[Optional[str], Any]:
        default_ref_d = {"filters": {"location": AGENTPOS}}
        ref_d = d.get("reference_object", default_ref_d)
        objs = self.subinterpret["reference_objects"](
            self, speaker, ref_d, extra_tags=["_physical_object"]
        )
        if len(objs) == 0:
            raise ErrorWithResponse("I don't know what you want me to get.")

        if all(isinstance(obj, PlayerNode) for obj in objs):
            raise ErrorWithResponse("I can't get a person, sorry!")
        objs = [obj for obj in objs if not isinstance(obj, PlayerNode)]

        if d.get("receiver") is None:
            receiver_d = None
        else:
            receiver_d = d.get("receiver").get("reference_object")
        receiver = None
        if receiver_d:
            receiver = self.subinterpret["reference_objects"](self, speaker, receiver_d)
            if len(receiver) == 0:
                raise ErrorWithResponse("I don't know where you want me to take it")
            receiver = receiver[0].memid

        tasks = []
        for obj in objs:
            task_data = {"get_target": obj.memid, "give_target": receiver, "action_dict": d}
            tasks.append(self.task_objects["get"](agent, task_data))
        #        logging.info("Added {} Get tasks to stack".format(len(tasks)))
        return maybe_task_list_to_control_block(tasks, agent), None, None

    def handle_dance(self, agent, speaker, d) -> Tuple[Optional[str], Any]:
        def new_tasks():
            repeat = get_repeat_num(d)
            tasks_to_do = []
            # only go around the x has "around"; FIXME allow other kinds of dances
            location_d = d.get("location")
            if location_d is not None:
                rd = location_d.get("relative_direction")
                if rd is not None and (
                    rd == "AROUND" or rd == "CLOCKWISE" or rd == "ANTICLOCKWISE"
                ):
                    ref_obj = None
                    location_reference_object = location_d.get("reference_object")
                    if location_reference_object:
                        objmems = self.subinterpret["reference_objects"](
                            self, speaker, location_reference_object
                        )
                        if len(objmems) == 0:
                            raise ErrorWithResponse("I don't understand where you want me to go.")
                        ref_obj = objmems[0]
                    refmove = dance.RefObjMovement(
                        agent,
                        ref_object=ref_obj,
                        relative_direction=location_d["relative_direction"],
                    )
                    t = self.task_objects["dance"](agent, {"movement": refmove})
                    return t

            dance_type = d.get("dance_type", {})
            if dance_type.get("point"):
                target = self.subinterpret["point_target"](self, speaker, dance_type["point"])
                t = self.task_objects["point"](agent, {"target": target})
            elif dance_type.get("look_turn") or dance_type.get("body_turn"):
                lt = dance_type.get("look_turn")
                if lt:
                    f = self.subinterpret["facing"](self, speaker, lt, head_or_body="head")
                    t = self.task_objects["look"](agent, f)
                else:
                    bt = dance_type.get("body_turn")
                    f = self.subinterpret["facing"](self, speaker, bt, head_or_body="body")
                    t = self.task_objects["turn"](agent, f)
            else:
                if location_d is None:
                    dance_location = None
                else:
                    mems = self.subinterpret["reference_locations"](self, speaker, location_d)
                    steps, reldir = interpret_relative_direction(self, location_d)
                    dance_location, _ = self.subinterpret["specify_locations"](
                        self, speaker, mems, steps, reldir
                    )
                filters_d = dance_type.get("filters", {})
                filters_d["memory_type"] = "DANCES"
                F = self.subinterpret["filters"](self, speaker, dance_type.get("filters", {}))
                dance_memids, _ = F()
                # TODO correct selector in filters
                if dance_memids:
                    dance_memid = random.choice(dance_memids)
                    dance_mem = self.memory.get_mem_by_id(dance_memid)
                    dance_obj = dance.Movement(
                        agent=agent, move_fn=dance_mem.dance_fn, dance_location=dance_location
                    )
                    t = self.task_objects["dance"](agent, {"movement": dance_obj})
                else:
                    # dance out of scope
                    raise ErrorWithResponse("I don't know how to do that movement yet.")
            return t

        if "remove_condition" in d:
            condition = self.subinterpret["condition"](self, speaker, d["remove_condition"])
            task_data = {"new_tasks": new_tasks, "remove_condition": condition, "action_dict": d}
            return self.task_objects["control"](agent, task_data), None, None
        else:
            return new_tasks(), None, None

    def handle_drop(self, agent, speaker, d) -> Tuple[Optional[str], Any]:
        """
        Drops whatever object in hand
        """

        return self.task_objects["drop"](agent, {"action_dict": d}), None, None
