import networkx as nx
import utils

class OntologyQueryBuilder():
    def __init__(self, ontoGraph, concepts):
        self.ontoGraph = ontoGraph
        self.orderBy_desc_trigger_words = ['most', 'largest', 'top', 'biggest', 'greatest', 'longest', 'highest', 'most']
        self.orderBy_asc_trigger_words = ['least', 'shortest', 'smallest', 'lowest']
        self.groupBy_trigger_words = ['group by']
        self.select_agg_func = {'sum' : 'Sum', 'count' : 'Count', 'average' : 'Avg', 
                                'minimum' : 'Min', 'maximum' : 'Max',
                                'many': 'Count', 'large' : 'Sum', 'big' : 'Sum',
                                'combined' : 'Sum', 'total' : 'Sum'}
        self.concepts = concepts

    def getOQL(self, nlq, selected_set, iRoot, iTree, dep):
        '''
        selected_set : list of (token, 'annotation type', 'ontology type', c_name, p_name, r_name, vg_word, pos_tag)
        annotation type = 0 -> 'md'
        annotation type = 1 -> 'iv'
        annotation type = 2 -> 'tr'
        annotation type = 3 -> 'ne'

        ontology type = 0 -> 'concept'
        ontology type = 1 -> 'property'
        ontology type = 2 -> 'relationship

        when ontology type is relationship
        selected_set : list of (token, 'annotation type', 'ontology type', c_name1, c_name2, r_name, vg_word, pos_tag)
        '''
        buf_from = self.getFrom(selected_set)
        buf_groupBy = self.getGroupBy(selected_set, dep)
        buf_select = self.getSelect(nlq, selected_set, dep, buf_groupBy)
        buf_orderBy = self.getOrderBy(selected_set, dep)
        buf_where = self.getWhere(nlq, selected_set, iRoot, iTree, buf_from, dep)

        return (buf_from, buf_groupBy, buf_select, buf_orderBy, buf_where)

    def getFrom(self, selected_set):
        buf = []
        for element in selected_set:
            # Add concept name to buf if ontology concept or property
            if element[2] == 0 or element[2] == 1:
                buf += [element[3]]
        return set(buf)

    def getGroupBy(self, selected_set, dep):
        # To-Do : need better dependency parsing
        # Currently, only check word right after 'group by'
        buf = []
        for num, item in dep.items():
            if item[0] in self.groupBy_trigger_words:
                next_word = dep[num+1][0]
                for element in selected_set:
                    if next_word in element[0] and element[2] != 2:
                        dis_prop = element[4] if element[4] else self.concepts[element[3]].default_dis_prop
                        buf += [(element[3], dis_prop)]
        return buf

    def getSelect(self, nlq, selected_set, dep, buf_groupBy):
        buf = []
        words = nlq.split(' ')
        
        # Find Direct Object
        d_token = None
        d_element = None
        for num, item in dep.items():
            if item[2] == 'dobj':
                d_token = item[0]
                break
        for element in selected_set:
            if element[0] == d_token:
                d_element = element
                break

        # Add explicit aggregation property
        for idx in range(len(words)):
            if words[idx] in self.select_agg_func.keys():
                
                # Pass if word is involved in the token
                tf = [words[idx] in element[0].split(' ') for element in selected_set]
                if True in tf:
                    continue

                agg_func = self.select_agg_func[words[idx]]
                dep_tokens = utils.traverseDependency(nlq, dep, selected_set, words[idx])
                if dep_tokens:
                    for element in selected_set:
                        # Select token with dependency
                        if element[0] == dep_tokens[0]:
                            agg_prop = self.concepts[element[3]].default_agg_prop if not element[4] else element[4]
                            buf += [(agg_func, element[3], agg_prop)]
                            break
                else:
                    # Select Closest token
                    element = selected_set[0]
                    agg_prop = self.concepts[element[3]].default_agg_prop if not element[4] else element[4]
                    buf += [(agg_func, element[3], agg_prop)]
                    break

        # Add implicit aggregation property
        if not buf and buf_groupBy and d_element:
            token = None
            if d_element[1] == 0 and d_element[2] != 2:
                # Check if already selected in groupBy
                same = False
                for tmp in buf_groupBy:
                    if d_element[3] == tmp[0] and d_element[4] == tmp[1]:
                        same = True
                if not same:
                    concept = self.concepts[d_element[3]]
                    key_agg_func = concept.default_agg_func
                    key_agg_prop = concept.default_agg_prop
                    buf += [(key_agg_func, element[3], key_agg_prop)]

            # Add other 
            for element in buf_groupBy:
                buf += [(None, *element)]
        
        # Find NN or NNS
        if not buf and words[0] not in ['how']:
            for element in selected_set:
                if element[1] == 0 and element[2] != 2:
                    try:
                        if element[7] in ['NN', 'NNS']:
                            prop = element[4] if element[4] else self.concepts[element[3]].default_dis_prop
                            tmp = (None, element[3], prop)
                            buf += [tmp]
                            break
                    except:
                        continue

        # Add display property
        if not buf:
            for element in selected_set:
                if element[1] == 0 and element[2] != 2:
                    prop = element[4] if element[4] else self.concepts[element[3]].default_dis_prop
                    tmp = (None, element[3], prop)
                    buf += [tmp]
                    break
        return buf

    def getOrderBy(self, selected_set, dep):
        # To-Do : need better dependency parsing
        # Currently, only check word right after one of trigger words
        buf = []
        for num, item in dep.items():
            if item[0] in self.orderBy_desc_trigger_words or item[0] in self.orderBy_asc_trigger_words:
                next_word = selected_set[0][0] if num+1 == len(dep) else dep[num+1][0]
                for element in selected_set:
                    if next_word in element[0] and element[2] != 2:
                        dis_prop = element[4] if element[4] else self.concepts[element[3]].default_agg_prop
                        order = ' desc' if item[0] in self.orderBy_desc_trigger_words else ' asc'
                        buf += [(element[3], dis_prop, order)]
                        break
        return buf

    def getWhere(self, nlq, selected_set, iRoot, iTree, buf_from, dep):
        # Binary Expression 1
        be1 = []
        for element in selected_set:
            if element[1] == 1:
                be1 += [(element[3], element[4], '=', element[6])]
            elif element[1] == 2:
                # To-Do : determine which operator to use
                be1 += [(element[3], element[4], '=', element[6])]
            elif element[1] == 3:
                # To-Do : determine which operator to use
                be1 += [(element[3], element[4], '=', element[6])]
                
        # Special rule for geo Data : Finding major city and rivers
        for idx, word in enumerate(nlq.split(' ')):
            if word == 'major':
                target_idx = dep[idx][1]
                target = dep[target_idx][0]
                for element in selected_set:
                    if target == element[0]:
                        prop = self.concepts[element[3]].default_agg_prop
                        value = '750' if element[3] == 'river' else '150000'
                        be1 += [(element[3], prop, '>', value)]
                        break
                break

        # Binary Expression 2
        be2 = []
        rnames = nx.get_edge_attributes(iTree, 'rname')
        for element in buf_from:
            if element == iRoot or element not in iTree.nodes:
                continue
            paths = nx.all_simple_paths(iTree, iRoot, element)
            paths = next(paths)
            path = []
            for i in range(len(paths)-1):
                rname = rnames[paths[i], paths[i+1]]
                path += [(paths[i], rname, paths[i+1])]
            be2 += [path]
        return [be1] + [be2]