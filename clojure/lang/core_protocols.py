"""The core protocols of Clojure.

Taken from ClojureScript's source.
"""

from .protocol import makeProtocol
from .. import protocols as protocols_namespace

# Store all protocols 
CLJS_PROTOCOLS = dict(
    IAssociative=["contains-key?", "assoc"],
    ICollection=["conj"],
    IComparable=["compare"],
    ICounted=["count"],
    IDeref=["deref"],
    IDerefWithTimeout=["deref-with-timeout"],
    IEditableCollection=["as-transient"],
    IEmptyableCollection=["empty"],
    IEquiv=["equiv"],
    IFn=["invoke"],
    IHash=["hash"],
    IIndexed=["nth"],
    IKVReduce=["kv-reduce"],
    IList=[],
    ILookup=["lookup"],
    IMap=["dissoc"],
    IMapEntry=["key", "val"],
    IMeta=["meta"],
    IOrdinal=["index"],
    IPending=["realized?"],
    IPrintable=["pr-seq"],
    IRecord=[],
    IReduce=["reduce"],
    IReversible=["rseq"],
    ISeqable=["seq"],
    ISeq=["first", "rest"],
    ISequential=[],
    ISet=["disjoin"],
    ISorted=["sorted-seq", "sorted-seq-from", "entry-key", "comparator"],
    IStack=["peek", "pop"],
    ITransientAssociative=["assoc!"],
    ITransientCollection=["conj!", "persistent!"],
    ITransientMap=["dissoc!"],
    ITransientSet=["disjoin!"],
    ITransientVector=["assoc-n!", "pop!"],
    IVector=["assoc-n"],
    IWatchable=["notify-watches", "add-watch", "remove-watch"],
    IWithMeta=["with-meta"],
)

CLJP_PROTOCOLS = dict( # XXX incomplete
    IDeref=["deref"],
    IEditableCollection=["asTransient"],
    IFn=["__call__"],
    IHashEq=["hasheq"],
    ILookup=["valAt"],
    IMeta=["meta"],
    IIndexed=["nth"],
    IObj=["withMeta"],
    IPersistentCollection=["count", "cons", "empty"], # Sequable
    IPersistentList=[], # Sequential, IPersisitentStack
    IPersistentMap=["without"], # Iterable, Associative, Counted
    IPersistentSet=["disjoin"], # IPersistentCollection, Counted
    IPersistentStack=["peek", "pop"], # IPersistentCollection
    IPersistentVector=["__len__", "assocN", "cons"], # Associative, Sequential, IPersistentStack, Reversible, Indexed)
    IPrintable=["writeAsString", "writeAsReplString"],
    IReduce=["reduce"],
    IReference=["alterMeta", "resetMeta"], # IMeta
    IRef=["setValidator", "getValidator", "getWatches", "addWatch", "removeWatch"], # IDeref
    ISeq=["first", "next", "more", "cons"],
    Iterable=["__iter__"],
    ITransientAssociative=["assoc"], # ITransientCollection, ILookup
    ITransientCollection=["conj", "persistent"],
    ITransientMap=["assoc", "without", "persistent"], # ITransientCollection, Counted
    Sequential=[],
) # and others...

PROTOCOLS = CLJP_PROTOCOLS

def make_protocolfn(fname):
    def protocolfn(*args):
        return None
    protocolfn.__name__ = fname
    return protocolfn

def init(protocols):
    for pname, fnames in protocols.items():
        setattr(protocols_namespace, pname,
                makeProtocol(protocols_namespace, pname, fnames))

init(PROTOCOLS)
