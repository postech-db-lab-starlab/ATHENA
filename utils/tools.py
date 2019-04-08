import string
import collections

def loadGeoDB():
    # Setup table and attributes
    db = dict()
    db_attribute = dict()
    mode = 0
    with open("./dataset/geo_test_ontology.meta") as f:
        for line in f.readlines():
            if line[0] == '#':
                continue
            elif line[0] == '-':
                break
            line = line.split(':')
            table_name = line[0]
            db[table_name] = dict()
            db_attribute[table_name] = []
            for i, attribute in enumerate(line[1].strip().split(',')):
                db[table_name][attribute] = []
                db_attribute[table_name] += [attribute]

    # Load values
    with open("./dataset/geodata") as f:
        for line in f.readlines():
            line = line.strip().split(':')
            table = line[0]
            values = line[1][1:-1].split(',')
            columns = db_attribute[table]
            for idx, column in enumerate(columns):
                db[table][column] += [values[idx].replace('\'', '')]

    # Remove duplication
    for table, columns in db.items():
        for key in columns.keys():
            columns[key] = set(columns[key])
            
    return db

def generateSelctedSets(set_list):
    buf = []
    if len(set_list) == 1:
        for item1 in set_list[0][2]:
            buf += [[(set_list[0][0], set_list[0][1], *item1, set_list[0][3])]]
    elif set_list:
        list2 = generateSelctedSets(set_list[1:])
        for item1 in set_list[0][2]:
            for item2 in list2:
                tmp = (set_list[0][0], set_list[0][1], *item1, set_list[0][3])
                buf += [[tmp] + item2]
    return buf

def preprocess(nlq):
    table = str.maketrans({key: None for key in string.punctuation})
    nlq = nlq.translate(table)
    nlq = nlq.lower().strip()
    if nlq[:-1] == ' ':
        nlq = nlq[:-1]
    return nlq

# Need a dictionary of synonym based on the context
def synDicPreprocess(syn_dic):
    '''
    syn_dic['country'].remove('state')
    syn_dic['country'].remove('area')
    syn_dic['state'].remove('tell')
    syn_dic['lowest point'].add('lowest spot')
    syn_dic['length'].add('long')
    syn_dic['number'].remove('total')
    syn_dic['population'].add('many people')
    syn_dic['population'].add('many citizens')
    syn_dic['population'].add('populous')
    syn_dic['population'].add('how large')
    syn_dic['population'].add('populated')
    syn_dic['area'].add('how large')
    syn_dic['area'].add('how big')
    syn_dic['height'].add('how high')
    syn_dic['highest elevation'].add('how high')
    syn_dic['run'].add('run through')
    syn_dic['run'].add('in')
    syn_dic['highest point'].add('high points')
    syn_dic['neighbor'].add('surrounding')
    syn_dic['neighbor'].add('bordering')
    '''


def traverseDependency(nlq, dep, selected_sets, rc_token):
    words = nlq.split(' ')
    for idx in range(len(words)):
        if words[idx] in rc_token:
            break

    dep_path = []
    while idx != -1:
        tmp = dep[idx]
        idx = tmp[1]
        dep_path += [tmp[0]]
    del dep_path[0]

    dep_tokens = []
    for token in dep_path:
        for ss in selected_sets:
            if ss[0] == token:
                dep_tokens += [ss[0]]

    return dep_tokens

def geoqueryParser(file_path):
    lines = []
    with open(file_path) as f:
        for line in f.readlines():
            line = line.strip().split(' = ')
            question = line[0]
            answer = []
            for tmp in line[1][1:-1].split(','):
                answer += [parseValue(tmp)]
            lines += [(question, answer)]
    return lines

def execute(db, sql):
    try:
        with db.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        db.commit()
    except:
        result = None
    return result

def evaluate(athena, db, q_and_a, target_num=None):
    parse_failure_cnt = 0
    sql_failure_cnt = 0
    t_cnt = 0
    f_cnt = 0
    num_buf = []

    for idx in range(len(q_and_a)):
        str_buf = []

        idx = target_num if target_num else idx
        question = q_and_a[idx][0]
        answer = q_and_a[idx][1]

        str_buf = '\n{}.){} ->\n'.format(idx, question)
        sqls = athena.forward(question)
        for sql in sqls:
            str_buf += '\t\t\t{}\n'.format(sql)

        if 'No output' in sqls[0]:
            parse_failure_cnt += 1
        else:
            correctness = []
            for sql in sqls:
                prediction = execute(db, sql)
                prediction = proprocess(prediction)
                # Show output
                if prediction is not None:
                    if compare(answer, prediction):
                        str_buf += 'Correct prediction...\n'
                        correctness += [1]
                    else:
                        str_buf += 'Wrong prediction...\n'
                        correctness += [0]

                    str_buf += '\tAnswer:{} prediction{}\n'.format(answer, prediction)
                else:
                    str_buf += '\tSQL Error...\n'
                    correctness += [2]
            
            # Count Result
            if 2 in correctness:
                sql_failure_cnt += 1
            #elif 0 not in correctness:
            elif 1 in correctness:
                t_cnt += 1
            else:
                f_cnt += 1

        # Print
        #if 'Wrong' in str_buf:
        if 'Correct' not in str_buf:
            print(str_buf)
            num_buf += [idx]

        if target_num:
            return

    print('incorrect answers: ')
    for item in num_buf:
        print(' ', item, end='')
    
    print('\nTotal:{} parse_failed:{} sql_failed:{}'.format(len(q_and_a), parse_failure_cnt, sql_failure_cnt))
    print('Correct:{} Wrong:{}'.format(t_cnt, f_cnt))

def stringToList(string):
    return None

def parseValue(value):
    try:
        return float(value)
    except:
        return value

def proprocess(prediction):
    buf = []
    if not prediction:
        return prediction

    for item in prediction:
        element = item[0]
        if not isinstance(element, str):
            if element not in buf:
                buf += [element]
        else:
            if ',' in element:
                for ele in element.split(','):
                    if ele not in buf:
                        buf += [ele]
            else:
                if element not in buf:
                    buf += [element]
    return buf

def compare(list1, list2):
    list1 = [] if list1 == [''] else list1
    return collections.Counter(list1) == collections.Counter(list2)