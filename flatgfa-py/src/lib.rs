use flatgfa::flatgfa::{FlatGFA, GFABuilder, HeapStore};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

#[pyfunction]
fn parse(filename: &str) -> PyFlatGFA {
    let file = flatgfa::file::map_file(filename);
    let store = flatgfa::parse::Parser::for_heap().parse_mem(file.as_ref());
    PyFlatGFA(InternalStore::Heap(store))
}

#[pyfunction]
fn load(filename: &str) -> PyFlatGFA {
    let mmap = flatgfa::file::map_file(filename);
    PyFlatGFA(InternalStore::File(mmap))
}

enum InternalStore {
    Heap(HeapStore),
    File(memmap::Mmap),
}

#[pyclass(frozen)]
#[pyo3(name = "FlatGFA")]
struct PyFlatGFA(InternalStore);

#[pymethods]
impl PyFlatGFA {
    #[getter]
    fn segments(self_: Py<Self>) -> SegmentList {
        SegmentList { gfa: GFARef(self_) }
    }
}

#[derive(Clone)]
struct GFARef(Py<PyFlatGFA>);

impl GFARef {
    fn view(&self) -> FlatGFA {
        // TK It seems wasteful to check the type of store every time... and to construct
        // the view every time. It would be great if we could somehow construct the view
        // once up front and hand it out to the various ancillary objects, but they need
        // to be assured that the store will survive long enough.
        match self.0.get().0 {
            InternalStore::Heap(ref store) => store.view(),
            InternalStore::File(ref mmap) => flatgfa::file::view(mmap),
        }
    }
}

#[pyclass]
struct SegmentList {
    gfa: GFARef,
}

#[pymethods]
impl SegmentList {
    fn __getitem__<'py>(&self, idx: u32) -> PySegment {
        PySegment {
            gfa: self.gfa.clone(),
            id: idx,
        }
    }

    fn __iter__(&self) -> SegmentIter {
        SegmentIter {
            gfa: self.gfa.clone(),
            idx: 0,
        }
    }

    fn __len__(&self) -> usize {
        self.gfa.view().segs.len()
    }
}

#[pyclass]
struct SegmentIter {
    gfa: GFARef,
    idx: u32,
}

#[pymethods]
impl SegmentIter {
    fn __iter__(self_: Py<Self>) -> Py<Self> {
        self_
    }

    fn __next__<'py>(&mut self) -> Option<PySegment> {
        let view = self.gfa.view();
        if self.idx < view.segs.len() as u32 {
            let seg = PySegment {
                gfa: self.gfa.clone(),
                id: self.idx,
            };
            self.idx += 1;
            Some(seg)
        } else {
            None
        }
    }
}

#[pyclass(frozen)]
#[pyo3(name = "Segment")]
struct PySegment {
    gfa: GFARef,
    #[pyo3(get)]
    id: u32,
}

#[pymethods]
impl PySegment {
    fn sequence<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        let view = self.gfa.view();
        let seg = view.segs[self.id as usize];
        let seq = view.get_seq(&seg);
        PyBytes::new_bound(py, seq) // TK Can we avoid this copy?
    }

    #[getter]
    fn name<'py>(&self) -> usize {
        let view = self.gfa.view();
        let seg = view.segs[self.id as usize];
        seg.name
    }

    fn __repr__(&self) -> String {
        format!("<Segment {}>", self.id)
    }
}

#[pymodule]
#[pyo3(name = "flatgfa")]
fn pymod(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_function(wrap_pyfunction!(load, m)?)?;
    Ok(())
}
