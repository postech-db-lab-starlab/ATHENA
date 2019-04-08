class QueryTranslator():
    def __init__(self, onto_to_db, db_primary_key):
        # To-Do : Need to implement those dictionary
        self.onto_to_db = onto_to_db
        self.db_primary_key = db_primary_key

    def getSQL(self, oql_bufs):
        buf_from = oql_bufs[0]
        buf_groupBy = oql_bufs[1]
        buf_select = oql_bufs[2]
        buf_orderBy = oql_bufs[3]
        buf_where = oql_bufs[4]

        from_clause = self.getFrom(buf_from)
        groupBy_clause = self.getGroupBy(buf_groupBy)
        select_clause = self.getSelect(buf_select)
        orderBy_clause = self.getOrderBy(buf_orderBy)
        where_clause = self.getWhere(buf_where)

        sql = 'SELECT ' + select_clause
        sql += ' FROM ' + from_clause if from_clause else ' '
        sql += ' WHERE ' + where_clause if where_clause else ' '
        sql += ' GROUP BY ' + groupBy_clause if groupBy_clause else ' '
        sql += ' ORDER BY ' + orderBy_clause if orderBy_clause else ' '
        return sql

    def getFrom(self, elements):
        # To-Do : There is additional line in the paper
        clause = ''
        for element in elements:
            table, _ = self.onto_to_db[(element, None)]
            clause += table + ', '
        return clause[:-2]

    def getGroupBy(self, elements):
        clause = ''
        for element in elements:
            table, column = self.onto_to_db[element]
            clause += table + '.' + column + ', '
        return clause[:-2]

    def getSelect(self, elements):
        clause = ''
        for element in elements:
            table, column = self.onto_to_db[(element[1], element[2])]
            if element[0]:
                clause += element[0] + '(' + table + '.' + column + '), '
            else:
                clause += table + '.' + column + ', '
        return clause[:-2]

    def getOrderBy(self, elements):
        clause = ''
        for element in elements:
            table, column = self.onto_to_db[(element[0], element[1])]
            clause += table + '.' + column + element[2] + ', '
        return clause[:-2] + ' limit 1' if clause else clause[:-2]

    def getWhere(self, elements):
        clause = ''
        for element in elements[0]:
            table, column = self.onto_to_db[(element[0], element[1])]
            clause += table + '.' + column + element[2] + '\''+ element[3] + '\' AND '

        for element in elements[1]:
            for path in element:
                if path[1] == 'is-a':
                    table_from, _ = self.onto_to_db[(path[0], None)]
                    key_from = self.db_primary_key[table_from]
                    table_to, _ = self.onto_to_db[(path[2], None)]
                    key_to = self.db_primary_key[table_to]
                    clause += table_from + '.' + key_from + '=' + table_to + '.' + key_to + 'AND '
                else:
                    table_from, _ = self.onto_to_db[(path[0], None)]
                    key_from = self.db_primary_key[table_from]
                    table_to, _ = self.onto_to_db[(path[2], None)]
                    key_to = self.db_primary_key[table_to]
                    clause += table_from + '.' + key_from + '=' + table_to + '.' + key_to + 'AND '            

        return clause[:-4]