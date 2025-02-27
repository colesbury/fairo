# Copyright (c) Facebook, Inc. and its affiliates.

# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


from yacs.config import CfgNode as CN

from pyrobot.cfg.config import get_cfg_defaults


_C = get_cfg_defaults()

_C.HAS_BASE = True
_C.HAS_CAMERA = True
_C.HAS_COMMON = True


# Camera specific setting
_CAMERAC = _C.CAMERA
# CAMERA class name
_CAMERAC.CLASS = "LoCoBotCamera"
# reset value for the pan
_CAMERAC.RESET_PAN = 0.0
# reset value for the tilt
_CAMERAC.RESET_TILT = 0.0
# camera depth map factor
_CAMERAC.DEPTH_MAP_FACTOR = 1.0

# Base specific settings
_BASEC = _C.BASE
# BASE class name
_BASEC.CLASS = "LoCoBotBase"
# BASE forward moving speed in m/s
_BASEC.FWD_SPEED = 1
# BASE turning speed in deg/s
_BASEC.TURN_SPEED = 30
# BASE simulation time step in sec
_BASEC.SIM_DT = 0.01


_COMMONC = _C.COMMON
# Name of the common class variable that will be shared in Robot class
_COMMONC.NAME = "simulator"
# Class type to assign to 'simulator' variable
_COMMONC.CLASS = "HabitatSim"

_C.COMMON.SIMULATOR = CN()

# Contains all of the simulator config
_SIMULATORC = _C.COMMON.SIMULATOR

_SIMULATORC.PHYSICS = False

_SIMULATORC.DEFAULT_AGENT_ID = 0

_SIMULATORC.SCENE_ID = "none"
_SIMULATORC.PHYSICS_CONFIG_FILE = "none"

# Contains the config of all the agents in simulation
_SIMULATORC.AGENT = CN()

_SIMULATORC.AGENT.NAME = ["realsense"]

# TODO: ADD agent- types, more agents, agent height, radius, actions etc

# Sensor config on the agent
_SIMULATORC.AGENT.SENSORS = CN()

# Set sensor names
_SIMULATORC.AGENT.SENSORS.NAMES = ["rgb", "depth", "semantic"]

# Set sensor type (COLOR, DEPTH, SEMANTIC)
_SIMULATORC.AGENT.SENSORS.TYPES = ["COLOR", "DEPTH", "SEMANTIC"]

# x, y, z and roll pitch yaw w.r.t to agent in meters and radians
# TODO: Check if these units are consistant with Habitat-sim
_SIMULATORC.AGENT.SENSORS.POSES = [
    [0.0, 0.6, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.6, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.6, 0.0, 0.0, 0.0, 0.0],
]
# Height and Widhth in Pixels
_SIMULATORC.AGENT.SENSORS.RESOLUTIONS = [[512, 512], [512, 512], [512, 512]]


def get_cfg():
    return _C.clone()
