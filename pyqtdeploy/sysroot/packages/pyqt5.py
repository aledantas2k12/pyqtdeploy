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

from ... import AbstractPackage, PackageOption


class PyQt5Package(AbstractPackage):
    """ The PyQt5 package. """

    # The package-specific options.
    options = [
        PackageOption('disabled_features', list,
                help="The features that are disabled."),
        PackageOption('modules', list, required=True,
                help="The extension modules to be built."),
        PackageOption('source', str, required=True,
                help="The archive containing the PyQt5 source code."),
    ]

    def build(self, sysroot):
        """ Build PyQt5 for the target. """

        sysroot.progress("Building PyQt5")

        # Unpack the source.
        archive = sysroot.find_file(self.source)
        sysroot.unpack_archive(archive)

        # Copy any license file.
        try:
            license = sysroot.find_file('pyqt-commercial.sip')
        except:
            license = None

        if license:
            sysroot.copy_file(license, 'sip')

        # Create a configuration file.
        cfg = '''py_platform = {0}
py_inc_dir = {1}
py_pylib_dir = {2}
py_pylib_lib = {3}
pyqt_module_dir = {4}
pyqt_sip_dir = {5}
[Qt 5]
pyqt_modules = {6}
'''.format(sysroot.target_py_platform, sysroot.target_py_include_dir,
                sysroot.target_lib_dir, sysroot.target_py_lib,
                sysroot.target_sitepackages_dir,
                os.path.join(sysroot.target_sip_dir, 'PyQt5'),
                ' '.join(self.modules))

        if self.disabled_features:
            cfg += 'pyqt_disabled_features = {0}\n'.format(
                    ' '.join(self.disabled_features))

        cfg_name = 'pyqt5-' + sysroot.target_arch_name + '.cfg'

        with open(cfg_name, 'wt') as cfg_file:
            cfg_file.write(cfg)

        # Configure, build and install.
        args = [sysroot.host_python, 'configure.py', '--static', '--qmake',
            sysroot.host_qmake, '--sysroot', sysroot.sysroot_dir, '--no-tools',
            '--no-qsci-api', '--no-designer-plugin', '--no-python-dbus',
            '--no-qml-plugin', '--no-stubs', '--configuration', cfg_name,
            '--sip', sysroot.host_sip, '--confirm-license', '-c', '-j2']

        if sysroot.verbose_enabled:
            args.append('--verbose')

        sysroot.run(*args)
        sysroot.run(sysroot.host_make)
        sysroot.run(sysroot.host_make, 'install')

    def configure(self, sysroot):
        """ Complete the configuration of the package. """

        if not sysroot.find_package('qt5').ssl:
            self.disabled_features.append('PyQt_SSL')
