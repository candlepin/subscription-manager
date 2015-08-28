#
# Read and parse /proc/cpuinfo
#
# Copyright (c) 2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

# needs to be able to provide a data object for each cpu blob and
# for the system
#
# needs to be able to aggregate multiple cpu data objects and create
# an exemplar cpuinfo  (ie, if we want to ignore cpus at different
# speeds, this may be where)
#
# needs to work non-root if possible, possibly as a standalone module/cli
#
# Expect the info available in cpuinfo to very across arches, and across
# kernel and cpu versions. Some arches have almost no info. Some have tons.
# Some provide hex values, most decimal.
#
# Expect the field names to change often. Don't expect field names to
# be unique.
#
# Expect some fields to disappear without warning at any oppurtunity
# (This includes changing arch, version, kernel, os vendor. It also includes
#  no reason at all. cpus can disappear. cpus can remove fields. they can
#  reappear).
#
# Expect values of cpuinfo fields to change, somethings constantly. cpu speed
# for example, can actually vary _every_ time it is read.
#
# GOTCHAS: the field names are non consistent across arches, and can conflict
#          semantically.
#
#         surprise, some are not even one key: value per line (see s390x)
#
# context manager?
# class CpuinfoFile()
#     .read()
#  handle io errors
#
# can take file like object or
# class BaseParseCpuInfo()
#
# class FieldNameCanonicalizer()
#  ie, convert 'model name' to model_name
#  and 'proccesor' processor
#  and 'Processor' to... seriously aarch64?
#    ('Processor' and 'processor' fields...)
#
# class CpuInfo() the main interface class
#     arch = None
#     cpuinfo_class = None
#     # avoid, count of cpus/sockets/etc
#
#
# class X86_64():
#
# class S390X():
#   with fun "multiple values per line"
#
# class Aarch64():
#   with hex values and a system stanza
#
# class Ppc64():
#    system stanza and system model
# factory to init proper one based... uname.machine? 'arch' file?

import collections

# mostly populated from the arm CPUID instruction
# http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.ddi0432c/Bhccjgga.html
# http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.ddi0432c/Chdeaeij.html
#
# aarch "version" info
# CPU implementer : 0x50
# CPU architecture: AArch64
# CPU variant : 0x0
# CPU part    : 0x000
# CPU revision    : 0

# Mostly info from intel CPUID instruction
# http://en.wikipedia.org/wiki/CPUID
#
# intel "version" info
# processor   : 22
# vendor_id   : GenuineIntel
# cpu family  : 6
# model       : 45
# model name  : Intel(R) Xeon(R) CPU E5-2630 0 @ 2.30GHz
# stepping    : 7
# microcode   : 0x710


# represent the data in /proc/cpuinfo, which may include multiple processors
class CpuinfoModel(object):
    def __init__(self, cpuinfo_data=None):
        # The contents of /proc/cpuinfo
        self.cpuinfo_data = cpuinfo_data

        # A iterable of CpuInfoModels, one for each processor in cpuinfo
        self.processors = []

        # prologues or footnotes not associated with a particular processor
        self.other = []

        # If were going to pretend all the cpus are the same,
        # what do they all have in common.
        self.common = None

        # model name    : Intel(R) Core(TM) i5 CPU       M 560  @ 2.67GHz
        self._model_name = None

        # a model number
        # "45" for intel processor example above
        self._model = None

    @property
    def count(self):
        return len(self.processors)

    @property
    def model_name(self):
        return self._model_name

    @property
    def model(self):
        return self._model

    def __str__(self):
        lines = []
        lines.append("Processor count: %s" % self.count)
        lines.append('model_name: %s' % self.model_name)
        lines.append("")
        for k in sorted(self.common.keys()):
            lines.append("%s: %s" % (k, self.common[k]))
        lines.append("")
        for k, v in self.other:
            lines.append("%s: %s" % (k, v))
        lines.append("")
        return "\n".join(lines)


class AbstractCpuFields(object):
    """Maps generic cpuinfo fields to the corresponding field from ProcessorModel.

    For, a cpu MODEL (a number or string that the cpu vendor assigns to that model of
    cpu, '45' for an intel Xeon for example)
    is in the 'model' field in /proc/cpuinfo, and the
    'model' in the sluggified field in X86_64ProcessorModel. For aarch64,
    the field 'cpu_part' is it's MODEL.
    """
    MODEL_NAME = "model_name"
    MODEL = "model"


class X86_64Fields(object):
    MODEL_NAME = 'model_name'
    MODEL = 'model'


class Aarch64Fields(object):
    MODEL = 'cpu_part'
    MODEL_NAME = 'model_name'


class Aarch64ProcessorModel(dict):
    "The info corresponding to the info about each aarch64 processor entry in cpuinfo"
    pass


class X86_64ProcessorModel(dict):
    "The info corresponding to the info about each X86_64 processor entry in cpuinfo"
    pass


class X86_64CpuinfoModel(CpuinfoModel):
    pass


class Aarch64CpuinfoModel(CpuinfoModel):
    @property
    def model_name(self):
        if self._model_name:
            return self._model_name

        if not self.common:
            return None

        return self.common.get(Aarch64Fields.MODEL, None)

    @property
    def model(self):
        if self._model:
            return self._model

        if not self.common:
            return None

        return self.common.get(Aarch64Fields.MODEL_NAME, None)


def fact_sluggify(key):
    """Encodes an arbitrary string to something that can be used as a fact name.

    ie, 'model_name' instead of 'Model name'
    whitespace -> _
    lowercase
    utf8
    escape quotes

    In theory, any utf8 would work
    """
    # yeah, terrible...
    return key.lower().strip().replace(' ', '_').replace('.', '_')


def fact_sluggify_item(item_tuple):
    newkey = fact_sluggify(item_tuple[0])
    return (newkey, item_tuple[1])


def split_key_value_generator(file_contents, line_splitter):
    for line in file_contents.splitlines():
        parts = line_splitter(line)
        if parts:
            yield parts


def line_splitter(line):
    # cpu family    : 6
    # model name    : Intel(R) Core(TM) i5 CPU       M 560  @ 2.67GHz
    parts = line.split(':', 1)
    if parts[0]:
        parts = [part.strip() for part in parts]
        return parts
    return None


"""
Processor   : AArch64 Processor rev 0 (aarch64)
processor   : 0
processor   : 1
processor   : 2
processor   : 3
processor   : 4
processor   : 5
processor   : 6
processor   : 7
Features    : fp asimd evtstrm
CPU implementer : 0x50
CPU architecture: AArch64
CPU variant : 0x0
CPU part    : 0x000
CPU revision    : 0

Hardware    : APM X-Gene Mustang board
"""

# TODO: This class is kind of a working sketch, it doesn't make a lot of sense
#       atm.
#
# FIXME: Intention was to try to make these classes somewhat functional


class Aarch64CpuInfo(object):
    def __init__(self):
        self.cpu_info = Aarch64CpuinfoModel()

    @classmethod
    def from_proc_cpuinfo_string(cls, proc_cpuinfo_string):
        aarch64_cpu_info = cls()
        aarch64_cpu_info._parse(proc_cpuinfo_string)

        return aarch64_cpu_info

    def _parse(self, cpuinfo_data):
        kv_iter = split_key_value_generator(cpuinfo_data, line_splitter)
        kv_list = [x for x in kv_iter]
        # Yes, there is a 'Processor' field and a 'processor' field, so
        # if 'Processor' exists, we use it as the model name
        kv_list = self._cap_processor_to_model_name_filter(kv_list)
        slugged_kv_list = self._fact_sluggify_item_filter(kv_list)
        # kind of duplicated
        self.cpu_info.common = self.gather_cpu_info_model(slugged_kv_list)
        self.cpu_info.processors = self.gather_processor_list(slugged_kv_list)

        # For now, 'hardware' is per
        self.cpu_info.other = self.gather_cpu_info_other(slugged_kv_list)

    def _fact_sluggify_item_filter(self, kv_list):
        return [fact_sluggify_item(item)
                for item in kv_list]

    def _cap_processor_to_model_name(self, item):
        if item[0] == 'Processor':
            item[0] = "model_name"
        return item

    def _cap_processor_to_model_name_filter(self, kv_list):
        return [self._cap_processor_to_model_name(item)
                for item in kv_list]

    def gather_processor_list(self, kv_list):
        processor_list = []
        for k, v in kv_list:
            if k != 'processor':
                continue
            # build a ProcessorModel subclass for each processor
            # to add to CpuInfoModel.processors list
            cpu_info_model = self.gather_cpu_info_model(kv_list)
            cpu_info_model['processor'] = v
            processor_list.append(cpu_info_model)
        return processor_list

    # FIXME: more generic would be to split the stanzas by empty lines in the
    # first pass
    def gather_cpu_info_other(self, kv_list):
        other_list = []
        for k, v in kv_list:
            if k == 'hardware':
                other_list.append([k, v])
        return other_list

    def gather_cpu_info_model(self, kv_list):
        cpu_data = Aarch64ProcessorModel()
        for k, v in kv_list:
            if k == 'processor' or k == 'hardware':
                continue
            cpu_data[k] = v
        return cpu_data


class X86_64CpuInfo(object):
    def __init__(self):
        self.cpu_info = X86_64CpuinfoModel()

    @classmethod
    def from_proc_cpuinfo_string(cls, proc_cpuinfo_string):
        x86_64_cpu_info = cls()
        x86_64_cpu_info._parse(proc_cpuinfo_string)

        return x86_64_cpu_info

    def _parse(self, cpuinfo_data):
        # ordered list
        #kv_list = self._key_value_list(cpuinfo_data)
        kv_iter = split_key_value_generator(cpuinfo_data, line_splitter)

        processors = []
        all_fields = set()
        for processor_stanza in self._split_by_processor(kv_iter):
            proc_dict = self.processor_stanza_to_processor_data(processor_stanza)
            #pp(proc_dict)
            processors.append(proc_dict)

            # keep track of fields as we see them
            all_fields = self._track_fields(all_fields, proc_dict.keys())

        self.cpu_info.common = self.find_shared_key_value_pairs(all_fields, processors)
        self.cpu_info.processors = processors
        self.cpu_info.cpuinfo_data = cpuinfo_data

    def _track_fields(self, fields_accum, fields):
        for field in fields:
            fields_accum.add(field)
        return fields_accum

    def find_shared_key_value_pairs(self, all_fields, processors):
        # smashem, last one wins
        smashed = collections.defaultdict(set)

        # build a dict of fieldname -> list of all the different values
        # so we can dump the variant ones.
        for field in all_fields:
            for k, v in [(field, processor.get(field)) for processor in processors]:
                if v is None:
                    continue
                smashed[k].add(v)

        # remove fields that can't be smashed to one value
        common_cpu_info = dict([(x, smashed[x].pop()) for x in smashed if len(smashed[x]) == 1])
        return common_cpu_info

    def processor_stanza_to_processor_data(self, stanza):
        "Take a list of k,v tuples, sluggify name, and add to a dict."
        cpu_data = X86_64ProcessorModel()
        cpu_data.update(dict([fact_sluggify_item(item) for item in stanza]))
        return cpu_data

    def _split_by_processor(self, kv_list):
        current_cpu = None
        for key, value in kv_list:
            if key == 'processor':
                if current_cpu:
                    yield current_cpu
                current_cpu = [(key, value)]
                continue

            # if we have garbage in and no start to processor info
            if current_cpu:
                current_cpu.append((key, value))

        # end of kv_list
        if current_cpu:
            yield current_cpu


class SystemCpuInfoFactory(object):
    uname_to_cpuinfo = {'x86_64': X86_64CpuInfo,
                        'aarch64': Aarch64CpuInfo}
    proc_cpuinfo_path = '/proc/cpuinfo'

    @classmethod
    def from_uname_machine(cls, uname_machine):
        if uname_machine not in SystemCpuInfoFactory.uname_to_cpuinfo:
            # er?
            raise NotImplementedError

        proc_cpuinfo_string = cls.open_proc_cpuinfo()

        arch_class = cls.uname_to_cpuinfo[uname_machine]
        return arch_class.from_proc_cpuinfo_string(proc_cpuinfo_string)

    @classmethod
    def open_proc_cpuinfo(cls):
        proc_cpuinfo_buf = ''
        with open(cls.proc_cpuinfo_path, 'r') as proc_cpuinfo_f:
            proc_cpuinfo_buf = proc_cpuinfo_f.read()
        return proc_cpuinfo_buf
