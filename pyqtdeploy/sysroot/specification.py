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


import importlib
import json

from ..user_exception import UserException
from .abstract_package import AbstractPackage


class Specification:
    """ Encapsulate the specification of a system root directory. """

    def __init__(self, spec_file, plugin_path):
        """ Initialise the object. """

        self.packages = []

        # Load the JSON file.
        with open(spec_file) as f:
            try:
                spec = json.load(f)
            except json.JSONDecodeError as e:
                raise UserException(
                        "{}:{}: {}".format(spec_file, e.lineno, e.msg))

        # Do a high level parse and import the plugins.
        for name, value in spec.items():
            if name == 'Description':
                # Check its type even though we don't actually use it.
                if not isinstance(value, str):
                    self._bad_type(name, spec_file)
            else:
                # Find the package's plugin.
                plugin = None

                # Search any user specified directories.
                if plugin_path:
                    for plugin_dir in plugin_path.split(os.pathsep):
                        plugin = self._plugin_from_file(name, plugin_dir)
                        if plugin is not None:
                            break

                # Search the included plugin packages.
                if plugin is None:
                    # The name of the package root.
                    package_root = '.'.join(__name__.split('.')[:-1])

                    for package in ('.packages', '.packages.contrib'):
                        plugin = self._plugin_from_package(name, package,
                                package_root)
                        if plugin is not None:
                            break
                    else:
                        raise UserException(
                                "unable to find a plugin for '{}'".format(
                                        name))

                # Create the package plugin.
                package = plugin()
                setattr(package, 'name', name)

                # Parse the package-specific options.
                if not isinstance(value, dict):
                    self._bad_type(name, spec_file)

                for cls in plugin.__mro__:
                    options = cls.__dict__.get('options')
                    if options:
                        self._parse_options(value, options, package, spec_file,
                                name)

                    if cls is AbstractPackage:
                        break

                unused = value.keys()
                if unused:
                    self._parse_error(
                            "unknown value(s): {}".format(', '.join(unused)),
                            spec_file, name)

                self.packages.append(package)

    def _plugin_from_file(self, name, plugin_dir):
        """ Try and load a package plugin from a file. """

        plugin_file = os.path.join(plugin_dir, name + '.py')
        spec = importlib.util.spec_from_file_location(name, plugin_file)
        plugin_module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(plugin_module)
        except FileNotFoundError:
            return None

        return self._plugin_from_module(name, plugin_module)

    def _plugin_from_package(self, name, package, package_root):
        """ Try and load a package plugin from a Python package. """

        rel_name = package + '.' + name

        try:
            plugin_module = importlib.import_module(rel_name,
                    package=package_root)
        except ImportError:
            return None

        return self._plugin_from_module(package_root + rel_name, plugin_module)

    def _plugin_from_module(self, fq_name, plugin_module):
        """ Get any plugin implementation from a module. """

        for package_type in plugin_module.__dict__.values():
            if isinstance(package_type, type):
                if issubclass(package_type, AbstractPackage):
                    # Make sure the type is defined in the plugin and not
                    # imported by it.
                    if package_type.__module__ == fq_name:
                        return package_type

        return None

    def _parse_options(self, json_array, options, target, spec_file, context):
        """ Parse a JSON array according to a set of options and add the
        corresponding values as attributes of a target object.
        """

        for option in options:
            value = json_array.get(option.name)

            if value is None:
                if option.required:
                    self._parse_error("no '{}' specified".format(option.name),
                            spec_file, context)

                # Create a default value.
                value = option.type()
            elif not isinstance(value, option.type):
                self._bad_type(option.name, spec_file, context)

            setattr(target, option.name, value)
            del json_array[option.name]

    def _bad_type(self, name, spec_file, context=None):
        """ Raise an exception when an option name has the wrong type. """

        self._parse_error("value of '{}' has an unexpected type".format(name),
                spec_file, context)

    def _parse_error(self, message, spec_file, context):
        """ Raise an exception for by an error in the specification file. """

        if context:
            exception = "{}: Package '{}': {}".format(spec_file, context,
                    message)
        else:
            exception = "{}: {}".format(spec_file, message)

        raise UserException(exception)
