import time
import inflect

from stanfordcorenlp import StanfordCoreNLP
import utils

tokens_to_ignore = ['is', 'in', 'me']

class Annotator():
    def __init__(self, concepts, syn_dic, db, db_to_onto, max_token_len):
        self.concepts = concepts
        self.syn_dic = syn_dic
        self.db = db
        self.db_to_onto = db_to_onto
        self.max_token_len = max_token_len
        #self.nlp = StanfordCoreNLP('http://corenlp.run', port=80)
        self.nlp = StanfordCoreNLP('http://localhost', port=9000)
        self.inflect = inflect.engine()

    def annotate(self, nlq):
        nlq_s = nlq.split(' ')
        num_of_words = len(nlq_s)
        bitmap = [0 for i in range(num_of_words)]
        
        dep = self.getDependency(nlq)
        pos = self.getPartOfSpeech(nlq)

        set_list = []
        for num in range(self.max_token_len, 0, -1):
            for idx in range(num_of_words - num + 1):
                if 1 not in bitmap[idx:idx+num]:
                    words = [nlq_s[i] for i in range(idx, idx+num)]
                    token = ' '.join(words)

                    candidates = self.metaDataAnnotation(token)

                    if token not in tokens_to_ignore:
                        candidates = candidates if candidates else self.indexedValueAnnotation(token)
                        candidates = candidates if candidates else self.timeRangeAnnotation(token)
                        candidates = candidates if candidates else self.numericExpressionAnnotation(token)

                    if candidates:
                        pos_tag = pos[nlq_s[idx+num-1]]
                        candidates += (pos_tag,)
                        set_list += [(idx, candidates)]
                        for i in range(idx, idx+num, 1):
                            bitmap[i] = 1

        # Sort list
        set_list.sort()
        set_list = [tmp[1] for tmp in set_list]
        
        # Apply relationship contraint
        set_list = self.getRelationConstraint(nlq, dep, set_list)

        return set_list, dep

    def metaDataAnnotation(self, token):
        # Try to match plural word first, if plural
        out = self.inflect.singular_noun(token)
        cyc_num = 2 if out else 1

        candidates = []
        for cnt in range(cyc_num):
            if candidates:
                break

            target = out if cnt else token
                
            for name, concept in self.concepts.items():
                if target in self.syn_dic[name]:
                    candidates += [(0, name, None, None, None)]
                for prop in concept.properties:
                    if target in self.syn_dic[prop]:
                        candidates += [(1, name, prop, None, None)]
                for rela in concept.relationships:
                    if target in self.syn_dic[rela]:
                        candidates += [(2, name, None, rela, None)]

        return (token, 0, candidates) if candidates else None

    def indexedValueAnnotation(self, token):
        candidates = []
        for table_name, table in self.db.items():
            for column_name, column in table.items():
                words = self.variantGeneration(token, table_name, column_name)
                for word in words:
                    if word in column:
                        concept, prop = self.db_to_onto[(table_name, column_name)]
                        # Prevent duplication
                        tmp = (1, concept, prop, None, word)
                        if tmp not in candidates:
                            candidates += [tmp]

        return (token, 1, candidates) if candidates else None

    def timeRangeAnnotation(self, token):
        tmp = (token, 2)
        return None

    def numericExpressionAnnotation(self, token):
        ner = self.nlp.ner(token)
        ne_bitmap = [tmp[1] == 'NUMBER' for tmp in ner]
        return (token, 3) if False not in ne_bitmap else None

    def variantGeneration(self, token, table_name, column_name):
        # To-Do: add rules to generate variant words
        tokens = [token]
        words = token.split(' ')
        '''
        #if len(words) == 2:
            #if table_name == 'city' and column_name == 'name' and words[0] in self.db['city']['name'] and words[1] in self.db['state']['name']:
            #    tokens += [words[0]]
            #if words[1] == 'river' and words[0] in self.db['river']['name']:
            #    tokens += [words[0]]
        ''' 
        
        if token in ['america', 'united states', 'us']:
            tokens += ['usa']
        
        #return [token]
        return tokens

    def getRelationConstraint(self, nlq, dep, selected_sets):
        ss = []
        for idx in range(len(selected_sets)):
            # If metadata
            if selected_sets[idx][1] == 0:
                buf = []
                for idx2 in range(len(selected_sets[idx][2])):
                    element = selected_sets[idx][2][idx2]
                    # If relationship
                    if element[0] == 2:
                        dep_tokens = utils.traverseDependency(nlq, dep, selected_sets, selected_sets[idx][0])
                        if len(dep_tokens) > 1:
                            buf += [(*element, dep_tokens[0], dep_tokens[1])]
                        elif idx != 0 and idx + 1 < len(selected_sets):
                            buf += [(*element, selected_sets[idx-1][0], selected_sets[idx+1][0])]
                        else:
                            # Find two element with nn
                            tmp = []
                            for idx2 in range(len(selected_sets)):
                                if idx != idx2 and selected_sets[idx2][3] in ['NN', 'NNS', 'VBZ']:
                                    tmp += [selected_sets[idx2][0]]
                            if len(tmp) > 1:
                                buf += [(*element, tmp[0], tmp[1])]
                    else:
                        buf += [element]
                if buf:
                    ss += [[selected_sets[idx][0], selected_sets[idx][1], buf, selected_sets[idx][3]]]
            else:
                ss += [selected_sets[idx]]
        return ss

    def getDependency(self, nlq):
        dep_dic = {}
        words = nlq.split(' ')
        dep = self.nlp.dependency_parse(nlq)
        
        for idx in range(len(dep)):
            dep_dic[dep[idx][2]-1] = (words[dep[idx][2]-1], dep[idx][1]-1, dep[idx][0])

        return dep_dic
    
    def getPartOfSpeech(self, nlq):
        pos_dic = {}
        pos = self.nlp.pos_tag(nlq)
        for tmp in pos:
            pos_dic[tmp[0]] = tmp[1]
        return pos_dic
