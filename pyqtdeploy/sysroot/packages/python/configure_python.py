# Copyright (c) 2017, Riverbank Computing Limited
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import os

from .patch import apply_diffs
from .pyconfig import generate_pyconfig_h


def configure_python(api, dynamic_loading, patches, sysroot):
    """ Configure a Python source directory for a particular target. """

    py_version_str = sysroot.format_version_nr(sysroot.py_version_nr)
    py_major, py_minor, py_patch = sysroot.decode_version_nr(
            sysroot.py_version_nr)

    sysroot.progress(
            "Configuring Python v{0} for {1}".format(py_version_str,
                    sysroot.target_name))

    py_src_dir = os.getcwd()

    configurations_dir = sysroot.get_embedded_dir(__file__, 'configurations')

    # Patch with the most appropriate diff.  Only Android needs patches and
    # only for Python earlier than v3.6.0.
    if patches and sysroot.target_name.startswith('android') and (py_major, py_minor) < (3, 6):
        python_diff_src_file = _get_file_for_version(py_version, 'patches',
                sysroot)

        # I'm too lazy to generate patches for all old versions.
        if python_diff_src_file == '':
            sysroot.error(
                    "Python v{0} is not supported on the {1} target".format(
                            py_version_str, sysroot.target_name))

        apply_diffs(python_diff_src_file, py_src_dir, sysroot)

    # Copy the modules config.c file.
    config_c_src_file = 'config_py{0}.c'.format(py_major)
    config_c_dst_file = os.path.join(py_src_dir, 'Modules', 'config.c')

    sysroot.progress("Installing {0}".format(config_c_dst_file))

    sysroot.copy_embedded_file(
            configurations_dir.absoluteFilePath(config_c_src_file),
            config_c_dst_file)

    # Generate the pyconfig.h file.  We follow the Python approach of a static
    # version for Windows and a dynamically created version for other
    # platforms.
    pyconfig_h_dst_file = os.path.join(py_src_dir, 'pyconfig.h')

    if sysroot.target_name.startswith('win'):
        sysroot.progress("Installing {0}".format(pyconfig_h_dst_file))

        pyconfig_h_src_file = _get_file_for_version(py_version, 'pyconfig',
                sysroot)

        sysroot.copy_embedded_file(pyconfig_h_src_file, pyconfig_h_dst_file,
                macros={
                    '@PY_DYNAMIC_LOADING@': '#define' if dynamic_loading else '#undef'})

        # Rename these otherwise MSVC confuses them with the ones we want to
        # use.
        pc_src_dir = os.path.join(py_src_dir, 'PC')

        for name in ('config.c', 'pyconfig.h'):
            try:
                os.rename(os.path.join(pc_src_dir, name),
                        os.path.join(pc_src_dir, name + '.orig'))
            except FileNotFoundError:
                pass
    else:
        if sysroot.target_name == 'android' and py_major == 3 and py_minor >= 6 and api < 21:
            sysroot.error(
                    "Python v3.6.0 and later requires Android API level 21 or later")

        sysroot.progress("Generating {0}".format(pyconfig_h_dst_file))

        generate_pyconfig_h(pyconfig_h_dst_file, api, dynamic_loading, sysroot)

    # Copy the python.pro file.
    python_pro_dst_file = os.path.join(py_src_dir, 'python.pro')

    sysroot.progress("Installing {0}".format(python_pro_dst_file))

    sysroot.copy_embedded_file(
            configurations_dir.absoluteFilePath('python.pro'),
            python_pro_dst_file,
            macros={
                '@PY_MAJOR_VERSION@': str(py_major),
                '@PY_MINOR_VERSION@': str(py_minor),
                '@PY_PATCH_VERSION@': str(py_patch),
                '@PY_DYNAMIC_LOADING@': 'enabled' if dynamic_loading else 'disabled'})


def _get_file_for_version(version, subdir, sysroot):
    """ Return the name of a file in a sub-directory of the 'configurations'
    directory that is most appropriate for a particular version.  An empty
    string is returned if the version is not supported.
    """

    return sysroot.get_embedded_file_for_version(version, __file__,
            'configurations', subdir)
