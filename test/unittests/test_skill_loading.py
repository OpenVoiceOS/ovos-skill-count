import unittest
from os.path import dirname

from ovos_plugin_manager.skills import find_skill_plugins
from ovos_utils.messagebus import FakeBus
from ovos_workshop.skill_launcher import PluginSkillLoader, SkillLoader

import ovos_skill_count
from ovos_skill_count import CountSkill


class TestSkillLoading(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.skill_id = "ovos-skill-count.openvoiceos"
        # this is a packaged skill: the source (__init__.py) + locale live inside
        # the ``ovos_skill_count`` package directory, not at the repo root, so the
        # SkillLoader must be pointed at the package dir.
        self.path = dirname(ovos_skill_count.__file__)

    def setUp(self):
        self.instances = []

    def tearDown(self):
        # each test may register bare skills and/or SkillLoader instances;
        # shut them all down so their background threads (event scheduler,
        # settings/file watchers) stop mutating shared bus/scheduler state
        # before pytest tears down the next test's fixtures
        for instance in self.instances:
            try:
                if isinstance(instance, SkillLoader):
                    instance.deactivate()
                else:
                    instance.default_shutdown()
            except Exception:
                pass

    def test_from_class(self):
        bus = FakeBus()
        skill = CountSkill()
        self.instances.append(skill)
        skill._startup(bus, self.skill_id)
        self.assertEqual(skill.bus, bus)
        self.assertEqual(skill.skill_id, self.skill_id)

    def test_from_plugin(self):
        bus = FakeBus()
        for skill_id, plug in find_skill_plugins().items():
            if skill_id == self.skill_id:
                skill = plug()
                self.instances.append(skill)
                skill._startup(bus, self.skill_id)
                self.assertEqual(skill.bus, bus)
                self.assertEqual(skill.skill_id, self.skill_id)
                break
        else:
            raise RuntimeError("plugin not found")

    def test_from_loader(self):
        bus = FakeBus()
        loader = SkillLoader(bus, self.path)
        self.instances.append(loader)
        loader.load()
        self.assertEqual(loader.instance.bus, bus)
        self.assertEqual(loader.instance.root_dir, self.path)

    def test_from_plugin_loader(self):
        bus = FakeBus()
        loader = PluginSkillLoader(bus, self.skill_id)
        self.instances.append(loader)
        for skill_id, plug in find_skill_plugins().items():
            if skill_id == self.skill_id:
                loader.load(plug)
                break
        else:
            raise RuntimeError("plugin not found")
        self.assertEqual(loader.skill_id, self.skill_id)
        self.assertEqual(loader.instance.bus, bus)
        self.assertEqual(loader.instance.skill_id, self.skill_id)
