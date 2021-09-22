import os
import logging

from subscription_manager import cpuinfo

from . import fixture

log = logging.getLogger("rhsm-app.unittests." + __name__)

test_path = os.path.dirname(__file__)
CPUINFOS = "data/cpuinfo"

cpu_data_dir = os.path.join(test_path, CPUINFOS)


class BaseCpuInfo(fixture.SubManFixture):
    expected = {}
    cpuinfo_class = None

    def _test(self, name):
        cpud = self._load_cpuinfo(name)
        exp = self.expected[name]

        x = self.cpuinfo_class.from_proc_cpuinfo_string(cpud)

        if 'cpu_count' in exp:
            self.assertEqual(exp['cpu_count'], len(x.cpu_info.processors))
        if 'model' in exp:
            self.assertEqual(exp['model'], x.cpu_info.model)
        if 'machine' in exp:
            self.assertEqual(exp['machine'], x.cpu_info.common['machine'])

    def _load_cpuinfo(self, name):
        f = open(os.path.join(cpu_data_dir, name), 'r')
        cpuinfo_data = f.read()
        return cpuinfo_data

    def _test_fact_key(self, key):
        bad_letters = ' .   '

        for bad_letter in bad_letters:
            self.assertFalse(bad_letter in key)


class TestX86_64CpuInfo(BaseCpuInfo):
    expected = {'x86_64-dell-e4310-1socket-2core-4cpu': {'cpu_count': 4,
                                                         'model': '37'},
                'x86_64-dell-t7600-2sockets-6core-24cpu': {'cpu_count': 24,
                                                           'model': '45'},
                'x86_64-4socket-8core-64cpu': {'cpu_count': 64},
                'armv7-samsung-1socket-2core-2cpu': {}}
    cpuinfo_class = cpuinfo.X86_64CpuInfo

    def test_x86_64_dell_e4310(self):
        self._test('x86_64-dell-e4310-1socket-2core-4cpu')

    def test_x86_64_64cpu(self):
        self._test('x86_64-4socket-8core-64cpu')

    def test_x86_64_24cpu_dell_t7600(self):
        self._test('x86_64-dell-t7600-2sockets-6core-24cpu')

    def test_armv7(self):
        # verify we fail nicely when given a completely different /proc/cpuinfo
        self._test('armv7-samsung-1socket-2core-2cpu')


class TestPpc64CpuInfo(BaseCpuInfo):
    cpuinfo_class = cpuinfo.Ppc64CpuInfo
    expected = {'ppc64-power8-16cpu-kvm':
                {'cpu_count': 16,
                 'platform': 'pSeries',
                 'model': 'IBM pSeries (emulated by qemu)'},
                'ppc64-power8-160cpu-powernv':
                    {'cpu_count': 160,
                     'platform': 'powerNV',
                     'model': '8247-22L'}}

    def test_ppc64_power8_160cpu_powernv(self):
        self._test('ppc64-power8-160cpu-powernv')

    def test_ppc64_power8_16cpu_kvm(self):
        self._test('ppc64-power8-16cpu-kvm')


class TestPpc64leCpuInfo(BaseCpuInfo):
    cpuinfo_class = cpuinfo.Ppc64CpuInfo
    expected = {'ppc64le-power8-16cpu-lpar':
                {'cpu_count': 16,
                 'platform': 'pSeries',
                 'model': 'IBM,8247-22L',
                 'machine': 'CHRP IBM,8247-22L'}
               }

    def test_ppc64le_power8_16cpu_lpar(self):
        self._test('ppc64le-power8-16cpu-lpar')


class TestAarch64CpuInfo(BaseCpuInfo):
    cpuinfo_class = cpuinfo.Aarch64CpuInfo
    expected = {'aarch64-mustang-dev-rhel7-1socket-8core-8cpu':
                {'cpu_count': 8,
                 'model_name': 'AArch64 Processor rev 0 (aarch64)'},
                'aarch64-hp-moonshot-1socket-8core-8cpu':
                    {'cpu_count': 8,
                     'model_name': None}}

    def test_mustang(self):
        self._test('aarch64-mustang-dev-rhel7-1socket-8core-8cpu')

    def test_moonshot(self):
        self._test('aarch64-hp-moonshot-1socket-8core-8cpu')
