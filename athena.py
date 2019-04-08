from owlready2 import *

import annotation
import iTree
import ontology
import query
import utils
import os

class Athena():
    def __init__(self, onto_name, max_token_len):
        self.onto_name = os.path.join('dataset', onto_name)
        self.owl_onto = get_ontology(self.onto_name + '.owl').load()
        self.max_token_len = max_token_len
        self.ontoParser = ontology.OntologyParser(self.onto_name + '.meta')
        self.concepts = self.ontoParser.parse(self.owl_onto)
        
        self.syn_dic = self.ontoParser.getSynonymDic(self.concepts)
        utils.synDicPreprocess(self.syn_dic)
        self.dics = self.ontoParser.getMapping(self.concepts)
        self.onto_to_db = self.dics[0]
        self.db_to_onto = self.dics[1]
        self.db_primary_key = self.dics[2]

        self.db = utils.loadGeoDB()
        self.annotator = annotation.Annotator(self.concepts, self.syn_dic, self.db, self.db_to_onto, self.max_token_len)

        self.iTreeGenerator = iTree.ITreeGenerator(self.concepts)
        self.nestedQueryDetector = query.NestedQueryDetector()
        self.ontologyQueryBuilder = query.OntologyQueryBuilder(self.iTreeGenerator.onto_graph, self.concepts)

        self.queryTranslator = query.QueryTranslator(self.onto_to_db, self.db_primary_key)

    def forward(self, nl):
        nlq = utils.preprocess(nl)
        set_list, dep = self.annotator.annotate(nlq)
        
        # Compose all possible selected sets
        selected_sets = utils.generateSelctedSets(set_list)

        # Check if any repeated ontology element
        selected_sets = self.checkRepetition(selected_sets, nlq, dep)

        # Generate iTree for every selected_sets
        candidates = []
        for selected_set in selected_sets:
            iTree = self.iTreeGenerator.getITree(selected_set)
            if iTree:
                candidates += [(selected_set, iTree)]

        # Select top iTree
        selected_set, selected_iTree = self.selectTopITree(candidates)

        if not selected_set:
            return ['No output : no selected_set']

        # Check if nested query
        selected_set = self.nestedQueryDetector.detect(selected_set)

        # Get OQL
        oqls = []
        for idx in range(len(selected_set)):
            iRoot = self.iTreeGenerator.getRoot(selected_iTree[idx])
            oql = self.ontologyQueryBuilder.getOQL(nlq, selected_set[idx], iRoot, selected_iTree[idx], dep)
            if oql[0] and oql[2]:
                oqls += [oql]

        if not oqls:
            return ['No output : no oql']

        # Get SQl
        sqls = []
        for oql in oqls:
            sql = self.queryTranslator.getSQL(oql)
            if sql not in sqls:
                sqls += [sql]

        return sqls

    def selectTopITree(self, candidates):
        top_score = float('inf')
        selected_set = []
        selected_iTree = []
        for candidate in candidates:
            score = self.iTreeGenerator.getITreeScore(candidate[0], candidate[1])
            if score < top_score:
                top_score = score
                selected_set = [candidate[0]]
                selected_iTree = [candidate[1]]
            elif score == top_score and candidate[0] not in selected_set:
                selected_set += [candidate[0]]
                selected_iTree += [candidate[1]]
        
        return selected_set, selected_iTree

    def checkRepetition(self, selected_sets, nlq, dep):
        tf = []
        for selected_set in selected_sets:
            buf = []
            for element in selected_set:
                # Check if already exist
                exist = [tmp[3] == element[3] and tmp[4] == element[4] and tmp[5] == element[5] for tmp in buf]
                if True in exist:
                    # Check if "and" or "is" dependency
                    try:
                        words = nlq.split(' ')
                        target_idx = len(exist) - 1 - exist[::-1].index(True)
                        idx = words.index(selected_set[target_idx][0])
                        if words[idx+1] in ['is', 'and', 'or']:
                            buf += [element]
                    except:
                        break
                else:
                    buf += [element]
            tf += [len(buf) == len(selected_set)]
        
        filtered_ss = []
        for idx, same in enumerate(tf):
            if same:
                filtered_ss += [selected_sets[idx]]

        return filtered_ss
