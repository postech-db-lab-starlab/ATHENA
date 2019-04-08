from athena import Athena
import utils
import pymysql

# Files
onto_file_path = 'geo_test_ontology'
max_token_len = 3
q_a_path = './dataset/question_answer.txt'

# Create
athena = Athena(onto_file_path, max_token_len)

# Load db
db = pymysql.connect(host='localhost', user='root', password='dblab123', db='test2')

q_and_a = utils.geoqueryParser(q_a_path)

# Get SQL
utils.evaluate(athena, db, q_and_a)

db.close()