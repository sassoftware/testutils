/*
 * Copyright (c) SAS Institute Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


#include <Python.h>
#include <frameobject.h>

typedef struct {
    PyObject_HEAD
    PyObject *lines;
    int enabled;
} CollectorObject;

staticforward PyTypeObject PyCollector_Type;

/* collector internal funtions */
static int
collector_callback(PyObject *self, PyFrameObject *frame, int what,
		   PyObject *arg)
{
    CollectorObject *co = (CollectorObject *) self;
    PyObject *t;
    switch (what) {
    case PyTrace_LINE:
	t = PyTuple_New(2);
	Py_INCREF(frame->f_code->co_filename);
	PyTuple_SetItem(t, 0, frame->f_code->co_filename);
	PyTuple_SetItem(t, 1, PyInt_FromLong(frame->f_lineno));
	Py_INCREF(Py_None);
	PyDict_SetItem(co->lines, t, Py_None);
	Py_DECREF(t);
	break;
    default:
	break;
    }
    return 0;
}

/* collector methods */
PyDoc_STRVAR(getlines_doc,
	     "getlines() -> dictionary of executed (file, lineno) tuples");
static PyObject*
collector_getlines(CollectorObject *self, PyObject *args, PyObject *kw)
{
    Py_INCREF(self->lines);
    return self->lines;
}

PyDoc_STRVAR(enable_doc, "enable() -> enable the coverage collector");
static PyObject*
collector_enable(CollectorObject *self, PyObject *args, PyObject *kw)
{
    /* Note: enabled might already be set, in which this _should_ be a 
       noop.  But rerunning it ensures that the correct settrace function
       is set */
    self->enabled = 1;
    PyEval_SetTrace(collector_callback, (PyObject*)self);
    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(disable_doc, "disable() -> disable the coverage collector");
static PyObject*
collector_disable(CollectorObject *self, PyObject *args, PyObject *kw)
{
    if (!self->enabled) {
	Py_INCREF(Py_None);
	return Py_None;
    }
    PyEval_SetTrace(NULL, NULL);
    self->enabled = 0;
    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(clear_doc, "clear() -> clear the coverage collector");
static PyObject*
collector_clear(CollectorObject *self, PyObject *args, PyObject *kw)
{
    PyDict_Clear(self->lines);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef collector_methods[] = {
    { "getlines", (PyCFunction)collector_getlines, METH_NOARGS, getlines_doc },
    { "enable",	(PyCFunction)collector_enable, METH_NOARGS, enable_doc },
    { "disable", (PyCFunction)collector_disable, METH_NOARGS, disable_doc },
    { "clear", (PyCFunction)collector_clear, METH_NOARGS, clear_doc },
    { NULL, NULL}
};

/* type implementation */
static void
collector_dealloc(CollectorObject *co)
{
    if (co->enabled)
	PyEval_SetTrace(NULL, NULL);
    Py_XDECREF(co->lines);
    co->ob_type->tp_free(co);
}

static int
collector_init(CollectorObject *co, PyObject *args, PyObject *kw)
{
    static char *kwlist[] = {0};
    if (!PyArg_ParseTupleAndKeywords(args, kw, "", kwlist))
	return -1;
    co->enabled = 0;
    co->lines = PyDict_New();
    return 0;
}

PyDoc_STRVAR(collector_doc, "A coverage collector");
statichere PyTypeObject PyCollector_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                      /* ob_size */
    "_coverage.Collector",                  /* tp_name */
    sizeof(CollectorObject),                /* tp_basicsize */
    0,                                      /* tp_itemsize */
    (destructor)collector_dealloc,          /* tp_dealloc */
    0,                                      /* tp_print */
    0,                                      /* tp_getattr */
    0,                                      /* tp_setattr */
    0,                                      /* tp_compare */
    0,                                      /* tp_repr */
    0,                                      /* tp_as_number */
    0,                                      /* tp_as_sequence */
    0,                                      /* tp_as_mapping */
    0,                                      /* tp_hash */
    0,                                      /* tp_call */
    0,                                      /* tp_str */
    0,                                      /* tp_getattro */
    0,                                      /* tp_setattro */
    0,                                      /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
    collector_doc,                          /* tp_doc */
    0,                                      /* tp_traverse */
    0,                                      /* tp_clear */
    0,                                      /* tp_richcompare */
    0,                                      /* tp_weaklistoffset */
    0,                                      /* tp_iter */
    0,                                      /* tp_iternext */
    collector_methods,                      /* tp_methods */
    0,                                      /* tp_members */
    0,                                      /* tp_getset */
    0,                                      /* tp_base */
    0,                                      /* tp_dict */
    0,                                      /* tp_descr_get */
    0,                                      /* tp_descr_set */
    0,                                      /* tp_dictoffset */
    (initproc)collector_init,               /* tp_init */
    PyType_GenericAlloc,                    /* tp_alloc */
    PyType_GenericNew,                      /* tp_new */
    PyObject_Del,                           /* tp_free */
};

static PyMethodDef modmethods[] = {
    { NULL, NULL }
};

PyMODINIT_FUNC
init_coverage(void)
{
    PyObject *module, *d;
    module = Py_InitModule3("_coverage", modmethods, "coverage collector");
    if (module == NULL)
	return;
    d = PyModule_GetDict(module);
    if (PyType_Ready(&PyCollector_Type) < 0)
	return;
    PyDict_SetItemString(d, "Collector", (PyObject *)&PyCollector_Type);
}
