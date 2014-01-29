# Copyright (c) 2014 Riverbank Computing Limited.
#
# This file is part of pyqtdeploy.
#
# This file may be used under the terms of the GNU General Public License
# v2 or v3 as published by the Free Software Foundation which can be found in
# the files LICENSE-GPL2.txt and LICENSE-GPL3.txt included in this package.
# In addition, as a special exception, Riverbank gives you certain additional
# rights.  These rights are described in the Riverbank GPL Exception, which
# can be found in the file GPL-Exception.txt in this package.
#
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.


import os
from xml.etree.ElementTree import Element, ElementTree, SubElement

from PyQt5.QtCore import QObject, pyqtSignal

from ..user_exception import UserException


class Project(QObject):
    """ The encapsulation of a project. """

    # The current project version.
    version = 0

    # Emitted when the modification state of the project changes.
    modified_changed = pyqtSignal(bool)

    @property
    def modified(self):
        """ The modified property getter. """

        return self._modified

    @modified.setter
    def modified(self, value):
        """ The modified property setter. """

        if self._modified != value:
            self._modified = value
            self.modified_changed.emit(value)

    # Emitted when the name of the project changes.
    name_changed = pyqtSignal(str)

    @property
    def name(self):
        """ The name property getter. """

        return self._name

    @name.setter
    def name(self, value):
        """ The name property setter. """

        if self._name != value:
            self._name = value
            self.name_changed.emit(value)

    def __init__(self):
        """ Initialise the project. """

        super().__init__()

        # Initialise the project meta-data.
        self._modified = False
        self.filename = ''
        self._name = ''

        # Initialise the project data.
        self.application_package = MfsPackage()
        self.application_script = ''
        self.pyqt_modules = []
        self.python_host_interpreter = ''
        self.python_target_include_dir = ''
        self.python_target_library = ''
        self.qt_is_shared = False

    @classmethod
    def load(cls, filename):
        """ Return a new project loaded from the given file.  Raise a
        UserException if there was an error.
        """

        abs_filename = os.path.abspath(filename)

        tree = ElementTree()

        try:
            root = tree.parse(abs_filename)
        except Exception as e:
            raise UserException(
                "There was an error reading the project file.", str(e))

        cls._assert(root.tag == 'Project',
                "Unexpected root tag '{0}', 'Project' expected.".format(
                        root.tag))

        # Check the project version number.
        version = root.get('version')
        cls._assert(version is not None, "Missing 'version' attribute.")

        try:
            version = int(version)
        except:
            version = None

        cls._assert(version is not None, "Invalid 'version'.")

        if version != cls.version:
            raise UserException(
                    "The project's format is version {0} but only version {1} is supported.".format(version, cls.version))

        # Create the project and populate it.
        project = cls()
        project._set_project_name(abs_filename)

        # The application specific configuration.
        application = root.find('Application')
        cls._assert(application is not None, "Missing 'Application' tag.")

        project.application_script = application.get('script', '')

        app_package = application.find('Package')
        cls._assert(app_package is not None,
                "Missing 'Application.Package' tag.")
        cls._load_package(app_package, project.application_package)

        for pyqt_m in application.iterfind('PyQtModule'):
            name = pyqt_m.get('name', '')
            cls._assert(name != '',
                    "Missing or empty 'PyQtModule.name' attribute.")
            project.pyqt_modules.append(name)

        # The Python specific configuration.
        python = root.find('Python')
        cls._assert(python is not None, "Missing 'Python' tag.")

        project.python_host_interpreter = python.get('hostinterpreter', '')
        project.python_target_include_dir = python.get('targetincludedir', '')
        project.python_target_library = python.get('targetlibrary', '')

        # The Qt specific configuration.
        qt = root.find('Qt')
        cls._assert(qt is not None, "Missing 'Qt' tag.")

        project.qt_is_shared = cls._get_bool(qt, 'isshared', 'Qt')

        return project

    def save(self):
        """ Save the project.  Raise a UserException if there was an error. """

        self._save_project(self.filename)

    def save_as(self, filename):
        """ Save the project to the given file and make the file the
        destination of subsequent saves.  Raise a UserException if there was an
        error.
        """

        abs_filename = os.path.abspath(filename)

        self._save_project(abs_filename)

        # Only do this after the project has been successfully saved.
        self._set_project_name(abs_filename)

    @classmethod
    def _load_package(cls, package_element, package):
        """ Populate an MfsPackage instance. """

        package.name = package_element.get('name')
        cls._assert(package.name is not None,
                "Missing 'Package.name' attribute.")

        package.contents = cls._load_mfs_contents(package_element)

        package.exclusions = []

        for exclude_element in package_element.iterfind('Exclude'):
            name = exclude_element.get('name', '')
            cls._assert(name != '',
                    "Missing or empty 'Package.Exclude.name' attribute.")
            package.exclusions.append(name)

    @classmethod
    def _load_mfs_contents(cls, mfs_element):
        """ Return a list of contents for a memory-filesystem container. """

        contents = []

        for content_element in mfs_element.iterfind('PackageContent'):
            isdir = cls._get_bool(content_element, 'isdirectory',
                    'Package.PackageContent')

            name = content_element.get('name', '')
            cls._assert(name != '',
                    "Missing or empty 'Package.PackageContent.name' attribute.")

            included = cls._get_bool(content_element, 'included',
                    'Package.PackageContent')

            content = MfsDirectory(name, included) if isdir else MfsFile(name, included)

            if isdir:
                content.contents = cls._load_mfs_contents(container_element)

            contents.append(content)

        return contents

    @classmethod
    def _get_bool(cls, element, name, context):
        """ Get a boolean attribute from an element. """

        value = element.get(name)
        try:
            value = int(value)
        except:
            value = None

        cls._assert(value is not None,
                "Missing or Invalid boolean value of '{0}.{1}'.".format(
                        context, name))

        return bool(value)

    def _set_project_name(self, abs_filename):
        """ Set the name of the project. """

        self.filename = abs_filename
        self.name = os.path.basename(abs_filename)

    def _save_project(self, abs_filename):
        """ Save the project to the given file.  Raise a UserException if there
        was an error.
        """

        root = Element('Project', attrib={
            'version': str(self.version)})

        application = SubElement(root, 'Application', attrib={
            'script': self.application_script})

        self._save_package(application, self.application_package)

        for pyqt_m in self.pyqt_modules:
            SubElement(application, 'PyQtModule', attrib={
                'name': pyqt_m})

        SubElement(root, 'Python', attrib={
            'hostinterpreter': self.python_host_interpreter,
            'targetincludedir': self.python_target_include_dir,
            'targetlibrary': self.python_target_library})

        SubElement(root, 'Qt', attrib={
            'isshared': str(int(self.qt_is_shared))})

        tree = ElementTree(root)

        try:
            tree.write(abs_filename, encoding='unicode', xml_declaration=True)
        except Exception as e:
            raise UserException(
                    "There was an error writing the project file.", str(e))

        self.modified = False

    @classmethod
    def _save_package(cls, container, package):
        """ Save a package in a container element. """

        package_element = SubElement(container, 'Package', attrib={
            'name': package.name})

        cls._save_mfs_contents(package_element, package.contents)

        for exclude in package.exclusions:
            SubElement(package_element, 'Exclude', attrib={
                'name': exclude})

    @classmethod
    def _save_mfs_contents(cls, container, contents):
        """ Save the contents of a memory-filesystem container. """

        for content in contents:
            isdir = isinstance(content, MfsDirectory)

            subcontainer = SubElement(container, 'PackageContent', attrib={
                'name': content.name,
                'included': str(int(content.included)),
                'isdirectory': str(int(isdir))})

            if isdir:
                cls._save_mfs_contents(subcontainer, content.contents)

    @staticmethod
    def _assert(ok, detail):
        """ Validate an assertion and raise a UserException if it failed. """

        if not ok:
            raise UserException("The project file is invalid.", detail)


class MfsPackage():
    """ The encapsulation of a memory-filesystem package. """

    def __init__(self):
        """ Initialise the project. """

        self.name = ''
        self.contents = []
        self.exclusions = ['*.pyc', '*.pyo', '__pycache__']


class MfsFile():
    """ The encapsulation of a memory-filesystem file. """

    def __init__(self, name, included):
        """ Initialise the file. """

        self.name = name
        self.included = included


class MfsDirectory(MfsFile):
    """ The encapsulation of a memory-filesystem directory. """

    def __init__(self, name, included):
        """ Initialise the directory. """

        super().__init__(name, included)

        self.contents = []
