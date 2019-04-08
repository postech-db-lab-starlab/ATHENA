import pymysql

def execute(db, sql):
    print(sql)
    try:
        with db.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        db.commit()
    except:
        result = None
    return result

# Strings
db_name = 'test2'
sql_template = 'Insert into %s values %s;'
table_file_path = './dataset/database_table'
value_file_name = './dataset/geobase'

# Load db
db = pymysql.connect(host='localhost', user='root', password='dblab123')

# Selected columns
dic = {
       'state' : [0, 2, 3, 4, 'population density', 'usa'],
       'city' : [0, 2, 3, 'usa'],
       'river' : [0, 1, 'usa', 'states'],
       'border' : [0, 'states'],
       'highlow' : [0, 2, 3, 4, 5],
       'mountain' : [0, 2, 3],
       'road' : [0, 'states'],
       'lake' : [0, 1, 'usa', 'states']
       }

# Create DB
execute(db, 'CREATE DATABASE IF NOT EXISTS {};'.format(db_name))
execute(db, 'use {};'.format(db_name))

# Create tables
with open(table_file_path) as f:
    lines = f.readlines()
    buf = ''
    for line in lines:
        line = line.strip()
        buf += line
        if ';' in line:
            execute(db, buf)
            buf = ''

# Insert values
wf = open('./dataset/geodata', 'w')
with open(value_file_name) as f:
    lines = f.readlines()
    mode = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not mode:
            if line[0] == '*':
                mode = 1
            continue

        table = line.split('(')[0]
        states = []

        # Parse value
        if '[' not in line:
            values = line[len(table)+1:-2].split(',')
        else:
            idx1 = line.find('[')
            idx2 = line.find(']')
            values = line[len(table)+1:idx1-1].split(',')
            if idx1+1 != idx2:
                line = line[idx1+1:idx2].split(',')
                for state in line:
                    states += [state]

        # Pass some data
        if table not in dic.keys():
            continue

        value = '('
        meta = dic[table]
        
        for tmp in meta:
            if isinstance(tmp, int):
                value += values[tmp] + ','
            elif tmp == 'usa':
                value += '\''+ tmp + '\','
            elif tmp == 'states':
                value += '%s,'
            elif tmp == 'population density':
                value += str(float(values[3]) / float(values[4])) + ','

        value = value[:-1] + ')'

        if 'states' in meta:
            for state in states:
                tmp = value % state
                execute(db, sql_template % (table, tmp))
                wf.write(table + ':' + tmp + '\n')
        else:
            execute(db, sql_template % (table, value))
            wf.write(table + ':' + value + '\n')

db.close()
wf.close()
print('done...')