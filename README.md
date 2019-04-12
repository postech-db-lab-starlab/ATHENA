# ATHENA

This module translates text into SQL. To use the module you will need to set up your local db, generate ontology based on db schema, and generate natural language and SQL pairs. For further information, please check test.py and athena.py

Also, ATHENA uses other parsing modules in stanford-corenlp. Thus, run local stanford-corenlp server with the command "java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -annotators "tokenize,ssplit,pos,lemma,parse,sentiment" -port 9000 -timeout 30000" before using ATHENA.

For improving the accuracy further, creating a powerful ontology and synonym dictionary is very important.
