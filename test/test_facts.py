import unittest
import tempfile
import json

from subscription_manager import facts



facts_buf = """
{
    "another": "blargh",
    "caneatcheese": "automatic100",
    "cpu.core(s)_per_socket": 4,
    "cpu.cpu(s)": 8,
    "cpu.cpu_mhz": "2420",
    "cpu.cpu_socket(s)": 2,
    "distribution.id": "Santiago",
    "distribution.name": "Red Hat Enterprise Linux Server",
    "distribution.version": "6.0",
    "dmi.baseboard.manufacturer": "Dell Inc.",
    "dmi.baseboard.product_name": "0RW203",
    "dmi.baseboard.serial_number": "..CN1374094G001M.",
    "dmi.baseboard.version": "",
    "dmi.bios.address": "0xf0000",
    "dmi.bios.bios_revision": "0.0",
    "dmi.bios.relase_date": "08/21/2008",
    "dmi.bios.rom_size": "1024 KB",
    "dmi.bios.runtime_size": "64 KB",
    "dmi.bios.vendor": "Dell Inc.",
    "dmi.bios.version": "A04",
    "dmi.chassis.asset_tag": "",
    "dmi.chassis.boot-up_state": "Warning",
    "dmi.chassis.lock": "Not Present",
    "dmi.chassis.manufacturer": "Dell Inc.",
    "dmi.chassis.power_supply_state": "Safe",
    "dmi.chassis.security_status": "None",
    "dmi.chassis.serial_number": "B654BK1",
    "dmi.chassis.thermal_state": "Safe",
    "dmi.chassis.type": "Tower",
    "dmi.chassis.version": "Not Specified",
    "dmi.connector.external_connector_type": "Mini Jack (headphones)",
    "dmi.connector.external_reference_designator": "Not Specified",
    "dmi.connector.internal_connector_type": "None",
    "dmi.connector.internal_reference_designator": "LINE-IN",
    "dmi.connector.port_type": "Audio Port",
    "dmi.memory.array_handle": "0x1000",
    "dmi.memory.assettag": "FFFFFF",
    "dmi.memory.bank_locator": "Not Specified",
    "dmi.memory.data_width": "64 bit",
    "dmi.memory.error_correction_type": "Multi-bit ECC",
    "dmi.memory.error_information_handle": "No Error",
    "dmi.memory.form_factor": "FB-DIMM",
    "dmi.memory.location": "System Board Or Motherboard",
    "dmi.memory.locator": "DIMM 4",
    "dmi.memory.manufacturer": "FFFFFFFFFFFF",
    "dmi.memory.maximum_capacity": "64 GB",
    "dmi.memory.part_number": "",
    "dmi.memory.serial_number": "FFFFFFFF",
    "dmi.memory.size": "4096 MB",
    "dmi.memory.speed": "667 MHz (1.5ns)",
    "dmi.memory.total_width": "72 bit",
    "dmi.memory.type": "DDR2 FB-DIMM",
    "dmi.memory.use": "System Memory",
    "dmi.processor.asset_tag": "Not Specified",
    "dmi.processor.family": "Xeon",
    "dmi.processor.l1_cache_handle": "0x0702",
    "dmi.processor.l2_cache_handle": "0x0703",
    "dmi.processor.part_number": "Not Specified",
    "dmi.processor.serial_number": "Not Specified",
    "dmi.processor.socket_designation": "CPU",
    "dmi.processor.status": "Populated:Idle",
    "dmi.processor.type": "Central Processor",
    "dmi.processor.upgrade": "Socket LGA771",
    "dmi.processor.version": "Not Specified",
    "dmi.processor.voltage": "1.1 V",
    "dmi.slot.current_usage": "Available",
    "dmi.slot.designation": "SLOT1",
    "dmi.slot.slotid": "1",
    "dmi.slot.slotlength": "Long",
    "dmi.slot.type:slotbuswidth": "x4",
    "dmi.slot.type:slottype": "PCI Express",
    "dmi.system.family": "Not Specified",
    "dmi.system.manufacturer": "Dell Inc.",
    "dmi.system.product_name": "Precision WorkStation T5400",
    "dmi.system.serial_number": "B654BK1",
    "dmi.system.sku_number": "Not Specified",
    "dmi.system.status": "No errors detected",
    "dmi.system.uuid": "44454c4c-3600-1035-8034-c2c04f424b31",
    "dmi.system.version": "Not Specified",
    "dmi.system.wake-up_type": "Power Switch",
    "lscpu.architecture": "x86_64",
    "lscpu.cpu_family": "6",
    "lscpu.cpu_mhz": "1995.095",
    "lscpu.cpu_op-mode(s)": "32-bit, 64-bit",
    "lscpu.cpu_socket(s)": "2",
    "lscpu.l1d_cache": "32K",
    "lscpu.l1i_cache": "32K",
    "lscpu.l2_cache": "6144K",
    "lscpu.model": "23",
    "lscpu.numa_node(s)": "1",
    "lscpu.numa_node0_cpu(s)": "0-7",
    "lscpu.stepping": "10",
    "lscpu.thread(s)_per_core": "1",
    "lscpu.vendor_id": "GenuineIntel",
    "lscpu.virtualization": "VT-x",
    "memory.memtotal": "10326220",
    "memory.swaptotal": "12419068",
    "nxxxw.tddng3": "10d0",
    "system.entitlements_valid": false,
    "test.attr": "blippy2",
    "uname.machine": "x86_64",
    "uname.release": "2.6.35.11-83.fc14.x86_64",
    "uname.sysname": "Linux",
    "uname.version": "#1 SMP Mon Feb 7 07:06:44 UTC 2011",
    "virt.host_type": "",
    "virt.is_guest": false
}

"""

def stub_get_facts():
    return {'newstuff':True}

class TestFacts(unittest.TestCase):
    def setUp(self):
        fact_cache_dir = tempfile.mkdtemp()
        fact_cache = fact_cache_dir + "/facts.json"
        print fact_cache
        fd = open(fact_cache, "w")
        fd.write(facts_buf)
        fd.close()
        self.f = facts.Facts()
        self.f.fact_cache_dir = fact_cache_dir
        self.f.fact_cache = fact_cache

    def test_facts_read(self):
        facts = self.f.read()
        self.assertEquals(facts["test.attr"], "blippy2")

    def test_facts_last_update(self):
        la = self.f.get_last_update()

    def test_facts_delta(self):
        self.f.get_facts = stub_get_facts
        delta = self.f.delta()
        self.assertEquals(delta["test.attr"], "blippy2")

    def test_get_facts(self):
        f = self.f.get_facts()
        self.assertEquals(f['net.interface.lo.ipaddr'], '127.0.0.1')

    def test_write_facts(self):
        fact_cache_dir = tempfile.mkdtemp()
        fact_cache = fact_cache_dir + "/facts.json"

        # write to a new file
        self.f.fact_cache_dir = fact_cache_dir
        self.f.fact_cache = fact_cache

        self.f.write({'empty.facts':1, 'otherthing':True})

        new_facts_buf = open(fact_cache).read()
        new_facts = json.loads(new_facts_buf)
        self.assertEquals(new_facts['empty.facts'], True)
