(ns clojure.core-multimethod
  (:require clojure.core-deftype)
  (:refer clojure.core-deftype))

(defprotocol IInitable
    (_init [self]))

(defprotocol IMultiFn
    (reset [self])
    (addMethod [self dispatchVal method])
    (removeMethod [self dispatchVal])
    (preferMethod [self dispatchValX dispatchValY])
    (prefers [self x y])
    (isA [self x y])
    (resetCache [self])
    (getMethod [self dispatchVal])
    (getFn [self dispatchVal])
    (findAndCacheBestMethod [self dispatchVal])
    (__call__ [& args])
    (getMethodTable [self])
    (getPreferTable [self]))

(deftype MultiFn [methodName 
                  dispatchFn 
                  defaultDispatchVal
                  hierarchy
                  methodTable
                  preferTable
                  methodCache
                  cachedHierarchy]
    IMultiFn
    (reset [self]
        (doseq [m ["methodTable"
                   "methodCache"
                   "preferTable"]]
            (py/setattr self m {}))
        (py/setattr self "cachedHierarchy" nil))
    
    (addMethod [self dispatchVal method]
        (py/setattr self 
                    "methodTable" 
                    (assoc (.getMethodTable self)
                           dispatchVal 
                           method))
        (.resetCache self))
    
    (removeMethod [self dispatchVal]
        (py/setattr self 
                    "methodTable" 
                    (dissoc (.getMethodTable self)
                            dispatchVal))
        (.resetCache self))
    
    (preferMethod [self x y]
        (if (.prefers self x y)
            (throw (py/Exception (str "Preference conflict in multimethod "
                                   methodName
                                   " "
                                   x
                                   " is already prefered to "
                                   y))))
        (py/setattr self
                    "preferTable"
                    (assoc (.getPreferTable self)
                           x
                           (conj (get (.getPreferTable self) x #{}) y)))
        (.resetCache self))

    (prefers [self x y]
        (let [xprefs (get (.getPreferTable self) x)]
             (cond (and (not (nil? xprefs)) 
                        (contains? xprefs y))
                    true
                   (some #(.prefers self x (first %)) (parents y))
                    true
                   (some #(.prefers self (first %) y) (parents x))
                    true
                   :default
                    false)))
    
    (isA [self x y]
        (isa? @hierarchy x y))
    
    (dominates [self x y]
        (or (.prefers self x y)
            (.isA self x y)))
    
    (resetCache [self]
        (py/setattr self "methodCache" (.getMethodTable self))
        (py/setattr self "cachedHierarchy" @hierarchy)
        methodCache)
    
    (getMethod [self dispatchVal]
        (if (not (= cachedHierarchy @hierarchy))
            (.resetCache self))
        (let [targetFn (get methodCache dispatchVal)]
             (if (not (nil? targetFn))
                 targetFn
                 (let [targetFn (.findAndCacheBestMethod self dispatchVal)]
                      (if (not (nil? targetFn))
                          targetFn
                          (get (.getMethodTable self)
                               defaultDispatchVal))))))
    
    (getFn [self dispatchVal]
        (let [targetFn (.getMethod self dispatchVal)]
             (if (nil? targetFn)
                 (throw (py/Exception (str "No method in multimethod " 
                                        methodName
                                        " for dispatch value "
                                        dispatchVal)))
                 targetFn)))
    
    (findAndCacheBestMethod [self dispatchVal]
      (let [be (reduce (fn [bestEntry e]
                      (if (.isA self dispatchVal (first e))
                          (if (or (nil? bestEntry) 
                                  (.dominates self (first e)
                                                   (first bestEntry)))
                              e
                              (if (not (.dominates self (first bestEntry)
                                                        (first e)))
                                  (throw (py/Exception (str "Multimple methods in multimethod "
                                                         methodName
                                                         " match dispatch value "
                                                         dispatchVal
                                                         " -> "
                                                         (first bestEntry)
                                                         " and "
                                                         (first e)
                                                         ", and neither is prefered")))
                                  bestEntry))
                          bestEntry))
                    nil
                    (.getMethodTable self))]
           (cond (nil? be)
                  nil
                 (is? cachedHierarchy @hierarchy)
                  (do (py/setattr self 
                                  "methodCache"
                                  (assoc methodCache
                                         dispatchVal
                                         (second be)))
                      (second be))
                  :default
                   (do (.resetCache self)
                       (.findAndCacheBestMethod self dispatchVal)))))
    
    (getMethodTable [self]
        (.-methodTable self))
    
    (getPreferTable [self]
        (.-preferTable self))
    
    (__call__ [self & args]
        (apply (.getFn self (apply dispatchFn args))
               args)))
                               
                
(defn make-multi [name dispatchFn defaultDispatchVal hierarchy]
    (MultiFn name dispatchFn defaultDispatchVal hierarchy
             {} {} {} nil))




