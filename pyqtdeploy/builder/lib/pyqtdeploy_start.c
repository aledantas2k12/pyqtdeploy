// Copyright (c) 2014, Riverbank Computing Limited
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
// 
// 1. Redistributions of source code must retain the above copyright notice,
//    this list of conditions and the following disclaimer.
// 
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.


#include <locale.h>
#include <stdio.h>
#include <string.h>

#include <Python.h>

#include "frozen_bootstrap.h"
#include "frozen_main.h"


#if PY_MAJOR_VERSION >= 3
#define BOOTSTRAP_MODULE    "_frozen_importlib"
#define PYQTDEPLOY_INIT     PyInit_pyqtdeploy
#define PYMAIN_TYPE         wchar_t
extern PyObject *PyInit_pyqtdeploy(void);
#else
#define BOOTSTRAP_MODULE    "__bootstrap__"
#define PYQTDEPLOY_INIT     initpyqtdeploy
#define PYMAIN_TYPE         char
extern void initpyqtdeploy(void);
#endif


// Foward declarations.
static int append_strings(PyObject *list, const char **values);


int pyqtdeploy_start(int argc, char **argv, PYMAIN_TYPE *py_main,
        const char *py_main_filename, struct _inittab *extension_modules,
        const char **path)
{
    // The replacement table of frozen modules.
    static struct _frozen modules[] = {
        {BOOTSTRAP_MODULE, frozen_pyqtdeploy_bootstrap, sizeof (frozen_pyqtdeploy_bootstrap)},
        {"__main__", frozen_pyqtdeploy_main, sizeof (frozen_pyqtdeploy_main)},
        {NULL, NULL, 0}
    };

    // The minimal sys.path.
    static const char *minimal_path[] = {
        ":/",
        ":/stdlib",
        ":/site-packages",
        NULL
    };

    PyObject *py_path, *mod, *mod_dict, *py_filename;
#if PY_MAJOR_VERSION >= 3
    wchar_t **w_argv;
    int i;
#if !defined(ANDROID)
    char *saved_locale;
#endif
#endif

    Py_FrozenFlag = 1;
    Py_NoSiteFlag = 1;
#if defined(ANDROID) && PY_MAJOR_VERSION >= 3
    Py_FileSystemDefaultEncoding = "utf-8";
#endif

    PyImport_FrozenModules = modules;

    // Add the importer to the table of builtins.
    if (PyImport_AppendInittab("pyqtdeploy", PYQTDEPLOY_INIT) < 0)
    {
        fprintf(stderr, "PyImport_AppendInittab() failed\n");
        return 1;
    }

    // Add any extension modules.
    if (extension_modules != NULL)
        if (PyImport_ExtendInittab(extension_modules) < 0)
        {
            fprintf(stderr, "PyImport_ExtendInittab() failed\n");
            return 1;
        }

#if PY_MAJOR_VERSION >= 3
    // Convert the argument list to wide characters.
    if ((w_argv = PyMem_Malloc(sizeof (wchar_t *) * argc)) == NULL)
    {
        fprintf(stderr, "PyMem_Malloc() failed\n");
        return 1;
    }

    w_argv[0] = py_main;

#if !defined(ANDROID)
    saved_locale = setlocale(LC_ALL, NULL);
    setlocale(LC_ALL, "");
#endif

    for (i = 1; i < argc; i++)
    {
        char *arg = argv[i];
        wchar_t *w_arg;
        size_t len;

#if !defined(ANDROID)
        len = mbstowcs(NULL, arg, 0);

        if (len == (size_t)-1)
        {
            fprintf(stderr, "Could not convert argument %d to string\n", i);
            return 1;
        }
#else
        char ch;

        len = strlen(arg);
#endif

        if ((w_arg = PyMem_Malloc((len + 1) * sizeof (wchar_t))) == NULL)
        {
            fprintf(stderr, "PyMem_Malloc() failed\n");
            return 1;
        }

        w_argv[i] = w_arg;

#if !defined(ANDROID)
        if (mbstowcs(w_arg, arg, len + 1) == (size_t)-1)
        {
            fprintf(stderr, "Could not convert argument %d to string\n", i);
            return 1;
        }
#else
        /* Convert according to PEP 383. */
        while ((ch = *arg++) != '\0')
        {
            if (ch <= 0x7f)
                *w_arg++ = ch;
            else
                *w_arg++ = 0xdc00 + ch;
        }
#endif
    }

#if !defined(ANDROID)
    setlocale(LC_ALL, saved_locale);
#endif

    // Initialise the Python v3 interpreter.
    Py_SetProgramName(w_argv[0]);
    Py_Initialize();
    PySys_SetArgv(argc, w_argv);
#else
    argv[0] = py_main;

    // Initialise the Python v2 interpreter.
    Py_SetProgramName(argv[0]);
    Py_Initialize();
    PySys_SetArgv(argc, argv);

    // Initialise the path hooks.
    if (PyImport_ImportFrozenModule(BOOTSTRAP_MODULE) < 0)
        goto py_error;
#endif

    // Configure sys.path.
    if ((py_path = PyList_New(0)) == NULL)
        goto py_error;

    if (append_strings(py_path, minimal_path) < 0)
        goto py_error;

    if (path != NULL && append_strings(py_path, path) < 0)
        goto py_error;

    if (PySys_SetObject("path", py_path) < 0)
        goto py_error;

    // Set the __file__ attribute of the main module.
    if ((mod = PyImport_AddModule("__main__")) == NULL)
        goto py_error;

    mod_dict = PyModule_GetDict(mod);

#if PY_MAJOR_VERSION >= 3
    py_filename = PyUnicode_FromString(py_main_filename);
#else
    py_filename = PyString_FromString(py_main_filename);
#endif

    if (py_filename == NULL)
        goto py_error;

    if (PyDict_SetItemString(mod_dict, "__file__", py_filename) < 0)
        goto py_error;

    Py_DECREF(py_filename);

    // Import the main module, ie. execute the application.
    if (PyImport_ImportFrozenModule("__main__") < 0)
        goto py_error;

    // Tidy up.
    Py_Finalize();

    return 0;

py_error:
    PyErr_Print();
    return 1;
}


// Extend a list with an array of strings.  Return -1 if there was an error.
static int append_strings(PyObject *list, const char **values)
{
    const char *value;

    while ((value = *values++) != NULL)
    {
        int rc;
        PyObject *py_value;

#if PY_MAJOR_VERSION >= 3
        py_value = PyUnicode_FromString(value);
#else
        py_value = PyString_FromString(value);
#endif

        if (py_value == NULL)
            return -1;

        rc = PyList_Append(list, py_value);
        Py_DECREF(py_value);

        if (rc < 0)
            return -1;
    }

    return 0;
}
