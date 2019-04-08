from subprocess import run, PIPE

q_cnt = 0
questions = ''
nl_questions = []
with open('../dataset/geoqueries250.txt') as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        idx = line.find('answer')
        question = line[idx:-2] + '.\n'
        questions += question
        nl_question = line[7:idx-3]
        nl_question = nl_question.replace(',', ' ')
        print(nl_question)
        nl_question = nl_question[:-2] + nl_question[-1]
        nl_questions += [nl_question]
        q_cnt += 1

facts = ''
with open('../dataset/geobase') as f:
    lines = f.readlines()
    mode = 0
    for line in lines:
        if line[0] == '\n':
            continue
        if not mode:
            if line[0] == '*':
                mode = 1
            continue
        facts += line + '\n'

input_text = 'compile(\'../dataset/geoquery\').\n'
input_text += facts
input_text += questions

f = open('output.txt', 'w')
p = run(['sicstus'], stdout=PIPE, input=input_text, encoding='ascii')
f.write(p.stdout)
f.close()

a_cnt = 0
tmp = []
with open('./output.txt') as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        a_cnt += 1
        tmp += [line]

assert(len(tmp) == len(nl_questions))
assert(q_cnt == a_cnt)

f = open('output.txt', 'w')
for idx in range(len(tmp)):
    line = tmp[idx].split(' = ')[1]
    line = nl_questions[idx] + ' = ' + line
    f.write(line + '\n')
f.close()