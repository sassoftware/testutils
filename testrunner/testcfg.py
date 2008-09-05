
from conary.lib import cfg
class TestConfig(cfg.ConfigFile):
    coverageDirs = cfg.CfgList(cfg.CfgPath)
    coverageExclusions = cfg.CfgList(cfg.CfgPath)
    isIndividual = cfg.CfgBool
    cleanTestDirs = cfg.CfgBool
