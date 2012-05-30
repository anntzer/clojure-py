(ns clojure.core-deftype)

(defn parse-impls
  "From a seq containing a both non-seqs and seqs, returns a map where the keys
  are the non-seqs, and the values are seqs of the seqs that come after each
  non-seq.  Seqs that occur before the first non-seq are dropped."
  [specs]
  (loop [ret {}
         s (drop-while seq? specs)]
    (if (seq s)
      (recur (assoc ret (first s) (take-while seq? (next s)))
             (drop-while seq? (next s)))
      ret)))

(defn wrap-specs
  "Given a type name, a seq of fields and a map of symbolic function names to
  function impls (of the form (sym [args+] body)), returns a map of string
  function names to functions named typename_fnname.  The function bodies are
  wrapped in a let-macro that makes each field available, being let-macro'd to
  the proper getattr."
  [name fields specs]
  (zipmap (map clojure.core/name (keys specs))
          (map #(prop-wrap-fn name fields %) (vals specs))))

(defn- protocol? [proto] (instance? clojure.lang.protocol/ProtocolMeta proto))

(defmacro deftype
  [name fields & specs]
  (let [impls (parse-impls specs)
        realfns (zipmap (keys impls)
                        (map #(->> (for [[name & _ :as all] (val %)] [name all])
                                (apply concat)
                                (apply hash-map)
                                (wrap-specs name fields))
                             impls))
        init (make-init fields)]
    `(let [all-methods# (remove (comp protocol? key) ~realfns)
           supers# (map key all-methods#)
           methods# (apply merge (map val all-methods#))
           methods# (assoc methods# "__init__" ~init)
           all-protofns# (filter (comp protocol? key) ~realfns)]
       (def ~name (py/type ~(clojure.core/name name)
                           (py/tuple supers#)
                           (.toDict methods#)))
       (doseq [[proto# protofns#] all-protofns#]
         (.extendForClass proto# ~name protofns#)))))

(defmacro defprotocol
  "A protocol is a named set of named methods and their signatures:

  (defprotocol AProtocolName
    ;optional doc string
    \"A doc string for AProtocol abstraction\"
  ;method signatures
    (bar [self a b] \"bar docs\")
    (baz [self a] [self a b] [self a b c] \"baz docs\"))

  No implementations are provided. Docs can be specified for the protocol
  overall and for each method. The above yields a set of polymorphic functions
  and a protocol object. All are namespace-qualified by the ns enclosing the
  definition The resulting functions dispatch on the type of their first
  argument, which is required and corresponds to the implicit target object
  ('self' in Python parlance). Implementations of the protocol methods can be
  provided using extend.

  (defprotocol P
    (foo [self])
    (bar-me [self] [this y]))

  (deftype Foo [a b c]
   P
    (foo [self] a)
    (bar-me [self] b)
    (bar-me [self y] (+ c y)))

  (bar-me (Foo 1 2 3) 42)
  => 45

  (foo
    (let [x 42]
      (reify P
        (foo [self] 17)
        (bar-me [self] x)
        (bar-me [self y] x))))
  => 17"
  [name & sigs]
  (let [docstr (when (string? (first sigs)) (first sigs))
        sigs (if docstr (next sigs) sigs)]
    `(do (def ~name (clojure.lang.protocol/makeProtocol
                      ~'*ns*
                      ~(clojure.core/name name)
                      (map #(str (clojure.core/name (first %))) '~sigs))))))

(defmacro reify 
  "reify is a macro with the following structure:

  (reify specs*)

  Each spec consists of the protocol or superclass name followed by zero or
  more method bodies:

  protocol-or-superclass
  (methodName [args+] body)*

  Methods should be supplied for all methods of the desired protocols. You can
  also define overrides for methods of any superclass (i.e., define arbitrary
  methods). Note that the first parameter must be supplied to correspond to the
  target object ('self' in Python parlance). Note also that recur calls to the
  method head should *not* pass the target object, it will be supplied
  automatically and can not be substituted.

  recur works to method heads. The method bodies of reify are lexical closures,
  and can refer to the surrounding local scope:
  
  (str (let [f \"foo\"] 
         (reify py/object
           (__str__ [self] f))))
  == \"foo\"

  (seq (let [f \"foo\"] 
         (reify clojure.protocols/Seqable
           (seq [self] (seq f)))))
  == (\\f \\o \\o))
  
  reify always implements clojure.lang.IObj and transfers meta data of the form
  to the created object.
  
  (meta ^{:k :v} (reify py/object (__str__ [self] \"foo\")))
  == {:k :v}"
  {:added "1.2"} 
  [& specs]
  (let [impls (parse-impls specs)
        realfns (zipmap (keys impls)
                        (map #(->> (for [[name & _ :as all] (val %)] [name all])
                                (apply concat)
                                (apply hash-map)
                                (wrap-specs name []))
                             impls))]
    `(let [all-methods# (remove (comp protocol? key) ~realfns)
           supers# (map key all-methods#)
           methods# (map val all-methods#)
           all-protofns# (filter (comp protocol? key) ~realfns)]
       (let [type# (py/type "reified"
                            (py/tuple supers#)
                            (.toDict (or (apply merge methods#) ~{})))]
         (doseq [[proto# protofns#] all-protofns#]
           (.extendForClass proto# type# protofns#))
         (type#)))))

(require 'copy)

(def recordfns) ; needed for recursive reasons

(def recordfns { "assoc" '(fn record-assoc
                               [self k v]
                               (let [copied (copy/copy self)]
                                    (py/setattr copied (name k) v)
                                    copied))
    
                 "containsKey" '(fn record-contains-key 
                                   [self k]
                                   (py/hasattr self (name k)))
                                   
                 "__contains__" '(fn __contains__
                                    [self k]
                                    (.containsKey self k))
                                    
                 "__getitem__" '(fn __getitem__
                                    [self k]
                                    (py/getattr self (name k)))                                    
                 
                 "entryAt"  '(fn entryAt
                                   [self k]
                                   (when (py/hasattr self (name k))
                                         (clojure.lang.mapentry/MapEntry 
                                             k
                                             (py/getattr self (name k)))))
                 "meta" '(fn meta
                            [self]
                            (if (.containsKey self :_meta)
                                (:_meta self)
                                nil))
                 
                 "withMeta" '(fn withMeta
                                 [self meta]
                                 (.assoc self :_meta meta))
                                 
                 "without" '(fn without
                                [self k]
                                (let [copied (copy/copy self)]
                                     (py/delattr copied (name k))
                                     copied))
                 "valAt" '(fn valAt
                              ([self k]
                               (.__getitem__ self (name k)))
                              ([self k default]
                               (if (.containsKey self k)
                                   (.valAt self k)
                                   default)))
                 
                 "keys" '(fn keys
                               [self]
                               (filter #(and (not (.startswith % "_"))
                                             (not (contains? (.-__methods__ self) %)))
                                        (py/dir self)))
                 
                 "count" '(fn count
                               [self]
                               (py/len (.keys self)))
                               
                 "empty" '(fn empty
                               [self]
                               (throw (clojure.core-deftype/AbstractMethodCall self)))
                               
                 ;; this may not be the fastest, but hey! it works. 
                 "__eq__" '(fn __eq__
                 	       [self other]
                 	       (if (py.bytecode/COMPARE_OP "is" self other)
                 	       	   true
                 	       	   (and (py.bytecode/COMPARE_OP "is"
                 	       	   	   (py/type self)
                 	       	   	   (py/type other))
                 	       	   	(every? identity (map = self other)) 
                 	       	   	(= (count self) (count other)))))
                 
                 "__hash__" '(fn __hash__
                 		[self]
                 		(if (py/hasattr self "_hash")
                 		     (py.bytecode/LOAD_ATTR "_hash" self)
                 		    (let [hash (reduce hash-combine 
                 		    		       (map #(py/getattr %2 %1) (keys self) (repeat self)))]
                 		    	 (py/setattr self "_hash" hash)
                 		    	 hash)))
                               
                 "seq" '(fn seq
                            [self]
                            (clojure.core-deftype/map #(.entryAt self %)
                                 (.keys self)))
                 
                 "__len__" '(fn len
                                [self]
                                (.count self))
                                
                 "cons" '(fn cons
                            [self [k v]]
                            (.assoc self k v))})

(defmacro defrecord
  [name fields & specs]
  (let [impls (parse-impls specs)
        realfns (zipmap (keys impls)
                        (map #(->> (for [[name & _ :as all] (val %)] [name all])
                                (apply concat)
                                (apply hash-map)
                                (wrap-specs name fields))
                             impls))
        init (make-init fields)]
    `(let [all-methods# (remove (comp protocol? key) ~realfns)
           supers# (map key all-methods#)
           methods# (->> all-methods# (apply concat) (apply hash-map))
           methods# (assoc methods# "__init__" ~init)
           methods# (merge ~recordfns methods#)
           methods# (assoc methods# "__methods__" methods#)
           all-protofns# (filter (comp protocol? key) ~realfns)]
       (def ~name (py/type ~(clojure.core/name name)
                           (py/tuple supers#)
                           (.toDict methods#)))
       (.extendForClass clojure.protocols/IPersistentMap ~name)
       (doseq [[proto# protofns#] all-protofns#]
         (.extendForClass proto# ~name protofns#)))))

(defn- emit-impl [[p fs]]
  [p (zipmap (map #(-> % first keyword) fs)
             (map #(cons 'fn (drop 1 %)) fs))])

(defn- emit-hinted-impl [c [p fs]]
  (let [hint (fn [specs]
               (let [specs (if (vector? (first specs)) 
                                        (list specs) 
                                        specs)]
                 (map (fn [[[target & args] & body]]
                        (cons (apply vector (vary-meta target assoc :tag c) args)
                              body))
                      specs)))]
    [p (zipmap (map #(-> % first name keyword) fs)
               (map #(cons 'fn (hint (drop 1 %))) fs))]))

(defn- emit-extend-type [c specs]
  (let [impls (parse-impls specs)]
    `(extend ~c
             ~@(mapcat (partial emit-hinted-impl c) impls))))

(defmacro extend-type 
  "A macro that expands into an extend call. Useful when you are
  supplying the definitions explicitly inline, extend-type
  automatically creates the maps required by extend.  Propagates the
  class as a type hint on the first argument of all fns.

  (extend-type MyType 
    Countable
      (cnt [c] ...)
    Foo
      (bar [x y] ...)
      (baz ([x] ...) ([x y & zs] ...)))

  expands into:

  (extend MyType
   Countable
     {:cnt (fn [c] ...)}
   Foo
     {:baz (fn ([x] ...) ([x y & zs] ...))
      :bar (fn [x y] ...)})"
  {:added "1.2"} 
  [t & specs]
  (emit-extend-type t specs))
