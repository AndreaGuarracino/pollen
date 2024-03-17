use crate::flatgfa::{FlatGFAStore, Handle, LineKind, Orientation};
use crate::gfaline;
use std::collections::HashMap;

#[derive(Default)]
pub struct Parser {
    /// The flat representation we're building.
    flat: FlatGFAStore,

    /// All segment IDs, indexed by their names, which we need to refer to segments in paths.
    seg_ids: NameMap,
}

/// Holds data structures that we haven't added to the flat representation yet.
struct Deferred {
    links: Vec<gfaline::Link>,
    paths: Vec<String>,
}

impl Parser {
    /// Parse a GFA text file.
    pub fn parse<R: std::io::BufRead>(stream: R) -> FlatGFAStore {
        let mut parser = Self::default();
        let mut deferred = Deferred {
            links: Vec::new(),
            paths: Vec::new(),
        };
        for line in stream.lines() {
            let line = line.unwrap();
            parser.parse_line(line, &mut deferred);
        }
        parser.finish(deferred)
    }

    /// Parse a single GFA line.
    ///
    /// We add *segments* to the flat representation immediately. We buffer *links* and *paths*
    /// in our internal vectors, because we must see all the segments first before we can
    /// resolve their segment name references.
    fn parse_line(&mut self, line: String, deferred: &mut Deferred) {
        // Avoid parsing paths entirely for now; just preserve the entire line for later.
        if line.as_bytes()[0] == b'P' {
            self.flat.record_line(LineKind::Path);
            deferred.paths.push(line);
            return;
        }

        let gfa_line = gfaline::parse_line(line.as_ref()).unwrap();
        match gfa_line {
            gfaline::Line::Header(data) => {
                self.flat.record_line(LineKind::Header);
                self.flat.add_header(data);
            }
            gfaline::Line::Segment(seg) => {
                self.flat.record_line(LineKind::Segment);
                let seg_id = self.flat.add_seg(seg.name, seg.seq, seg.data);
                self.seg_ids.insert(seg.name, seg_id);
            }
            gfaline::Line::Link(link) => {
                self.flat.record_line(LineKind::Link);
                deferred.links.push(link);
            }
            gfaline::Line::Path(_) => {
                unreachable!("paths handled separately")
            }
        }
    }

    fn add_link(&mut self, link: gfaline::Link) {
        let from = Handle::new(self.seg_ids.get(link.from_seg), link.from_orient);
        let to = Handle::new(self.seg_ids.get(link.to_seg), link.to_orient);
        self.flat.add_link(from, to, link.overlap);
    }

    fn add_path(&mut self, path: gfaline::Path) {
        let steps = gfaline::StepsParser::new(&path.steps).map(|(name, dir)| {
            Handle::new(
                self.seg_ids.get(name),
                if dir {
                    Orientation::Forward
                } else {
                    Orientation::Backward
                },
            )
        });
        self.flat
            .add_path(path.name, steps.into_iter(), path.overlaps.into_iter());
    }

    /// Finish parsing and return the flat representation.
    ///
    /// We "unwind" the buffers of links and paths, now that we have all
    /// the segments.
    fn finish(mut self, deferred: Deferred) -> FlatGFAStore {
        for link in deferred.links {
            self.add_link(link);
        }
        for line in deferred.paths {
            match gfaline::parse_line(line.as_ref()).unwrap() {
                gfaline::Line::Path(path) => self.add_path(path),
                _ => panic!("non-path line deferred"),
            };
        }
        self.flat
    }
}

#[derive(Default)]
struct NameMap {
    /// Names at most this are assigned *sequential* IDs, i.e., the ID is just the name
    /// minus one.
    sequential_max: usize,

    /// Non-sequential names go here.
    others: HashMap<usize, u32>,
}

impl NameMap {
    fn insert(&mut self, name: usize, id: u32) {
        // Is this the next sequential name? If so, no need to record it in our hash table;
        // just bump the number of sequential names we've seen.
        if (name - 1) == self.sequential_max && (name - 1) == (id as usize) {
            self.sequential_max += 1;
        } else {
            self.others.insert(name, id);
        }
    }

    fn get(&self, name: usize) -> u32 {
        if name <= self.sequential_max {
            (name - 1) as u32
        } else {
            self.others[&name]
        }
    }
}
