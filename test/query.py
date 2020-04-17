#
# Copyright (C) 2018, 2020 Oracle and/or its affiliates. All rights reserved.
#
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl
#
# Please see LICENSE.txt file included in the top-level directory of the
# appropriate download for a copy of the license and additional information.
#

import unittest
from collections import OrderedDict
from decimal import Context, ROUND_HALF_EVEN
from time import time

from borneo import (
    Consistency, GetRequest, IllegalArgumentException, PrepareRequest,
    PutRequest, QueryRequest, TableLimits, TableNotFoundException, TableRequest,
    TimeToLive, WriteMultipleRequest)
from parameters import is_onprem, table_name, tenant_id, timeout
from testutils import get_handle_config, get_row
from test_base import TestBase


class TestQuery(unittest.TestCase, TestBase):
    @classmethod
    def setUpClass(cls):
        cls.set_up_class()
        index_name = 'idx_' + table_name
        create_statement = (
            'CREATE TABLE ' + table_name + '(fld_sid INTEGER, fld_id INTEGER, \
fld_long LONG, fld_float FLOAT, fld_double DOUBLE, fld_bool BOOLEAN, \
fld_str STRING, fld_bin BINARY, fld_time TIMESTAMP(6), fld_num NUMBER, \
fld_json JSON, fld_arr ARRAY(STRING), fld_map MAP(STRING), \
fld_rec RECORD(fld_id LONG, fld_bool BOOLEAN, fld_str STRING), \
PRIMARY KEY(SHARD(fld_sid), fld_id))')
        limits = TableLimits(100, 100, 1)
        create_request = TableRequest().set_statement(
            create_statement).set_table_limits(limits)
        cls.table_request(create_request)

        create_idx_request = TableRequest()
        create_idx_statement = (
            'CREATE INDEX ' + index_name + '1 ON ' + table_name + '(fld_long)')
        create_idx_request.set_statement(create_idx_statement)
        cls.table_request(create_idx_request)
        create_idx_statement = (
            'CREATE INDEX ' + index_name + '2 ON ' + table_name + '(fld_str)')
        create_idx_request.set_statement(create_idx_statement)
        cls.table_request(create_idx_request)
        create_idx_statement = (
            'CREATE INDEX ' + index_name + '3 ON ' + table_name + '(fld_bool)')
        create_idx_request.set_statement(create_idx_statement)
        cls.table_request(create_idx_request)
        create_idx_statement = (
            'CREATE INDEX ' + index_name + '4 ON ' + table_name +
            '(fld_json.location as point)')
        create_idx_request.set_statement(create_idx_statement)
        cls.table_request(create_idx_request)
        global prepare_cost
        prepare_cost = 2
        global query_statement
        query_statement = ('SELECT fld_sid, fld_id FROM ' + table_name +
                           ' WHERE fld_sid = 1')

    @classmethod
    def tearDownClass(cls):
        cls.tear_down_class()

    def setUp(self):
        self.set_up()
        self.handle_config = get_handle_config(tenant_id)
        self.min_time = list()
        self.max_time = list()
        shardkeys = 2
        ids = 6
        write_multiple_request = WriteMultipleRequest()
        for sk in range(shardkeys):
            for i in range(ids):
                row = get_row()
                if i == 0:
                    self.min_time.append(row['fld_time'])
                elif i == ids - 1:
                    self.max_time.append(row['fld_time'])
                row['fld_sid'] = sk
                row['fld_id'] = i
                row['fld_bool'] = False if sk == 0 else True
                row['fld_str'] = (
                    '{"name": u' +
                    str(shardkeys * ids - sk * ids - i - 1).zfill(2) + '}')
                row['fld_json']['location']['coordinates'] = (
                    [23.549 - sk * 0.5 - i, 35.2908 + sk * 0.5 + i])
                write_multiple_request.add(
                    PutRequest().set_value(row).set_table_name(table_name),
                    True)
            self.handle.write_multiple(write_multiple_request)
            write_multiple_request.clear()
        prepare_statement_update = (
            'DECLARE $fld_sid INTEGER; $fld_id INTEGER; UPDATE ' + table_name +
            ' u SET u.fld_long = u.fld_long + 1 WHERE fld_sid = $fld_sid ' +
            'AND fld_id = $fld_id')
        prepare_request_update = PrepareRequest().set_statement(
            prepare_statement_update)
        self.prepare_result_update = self.handle.prepare(
            prepare_request_update)
        prepare_statement_select = (
            'DECLARE $fld_long LONG; SELECT fld_sid, fld_id, fld_long FROM ' +
            table_name + ' WHERE fld_long = $fld_long')
        prepare_request_select = PrepareRequest().set_statement(
            prepare_statement_select)
        self.prepare_result_select = self.handle.prepare(
            prepare_request_select)
        self.query_request = QueryRequest().set_timeout(timeout)
        self.get_request = GetRequest().set_table_name(table_name)

    def tearDown(self):
        self.tear_down()

    def testQuerySetIllegalCompartment(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_compartment, {})
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_compartment, '')

    def testQuerySetIllegalLimit(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_limit, 'IllegalLimit')
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_limit, -1)

    def testQuerySetIllegalMaxReadKb(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_max_read_kb,
                          'IllegalMaxReadKb')
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_max_read_kb, -1)

    def testQuerySetIllegalMaxWriteKb(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_max_write_kb,
                          'IllegalMaxWriteKb')
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_max_write_kb, -1)

    def testQuerySetIllegalMaxMemoryConsumption(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_max_memory_consumption,
                          'IllegalMaxMemoryConsumption')
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_max_memory_consumption, -1)

    def testQuerySetIllegalMathContext(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_math_context,
                          'IllegalMathContext')

    def testQuerySetIllegalConsistency(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_consistency,
                          'IllegalConsistency')

    def testQuerySetIllegalStatement(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_statement, {})
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_statement, '')
        self.query_request.set_statement('IllegalStatement')
        self.assertRaises(IllegalArgumentException, self.handle.query,
                          self.query_request)
        self.query_request.set_statement('SELECT fld_id FROM IllegalTableName')
        self.assertRaises(TableNotFoundException, self.handle.query,
                          self.query_request)

    def testQuerySetIllegalPreparedStatement(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_prepared_statement,
                          'IllegalPreparedStatement')

    def testQuerySetIllegalTimeout(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_timeout, 'IllegalTimeout')
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_timeout, 0)
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_timeout, -1)

    def testQuerySetIllegalDefaults(self):
        self.assertRaises(IllegalArgumentException,
                          self.query_request.set_defaults, 'IllegalDefaults')

    def testQuerySetDefaults(self):
        self.query_request.set_defaults(self.handle_config)
        self.assertEqual(self.query_request.get_timeout(), timeout)
        self.assertEqual(self.query_request.get_consistency(),
                         Consistency.ABSOLUTE)

    def testQueryNoStatementAndBothStatement(self):
        self.assertRaises(IllegalArgumentException, self.handle.query,
                          self.query_request)
        self.query_request.set_statement(query_statement)
        self.query_request.set_prepared_statement(self.prepare_result_select)
        self.assertRaises(IllegalArgumentException, self.handle.query,
                          self.query_request)

    def testQueryGets(self):
        context = Context(prec=10, rounding=ROUND_HALF_EVEN)
        self.query_request.set_consistency(Consistency.EVENTUAL).set_statement(
            query_statement).set_prepared_statement(
            self.prepare_result_select).set_limit(3).set_max_read_kb(
            2).set_max_write_kb(3).set_max_memory_consumption(
            5).set_math_context(context)
        self.assertIsNone(self.query_request.get_compartment())
        self.assertTrue(self.query_request.is_done())
        self.assertEqual(self.query_request.get_limit(), 3)
        self.assertEqual(self.query_request.get_max_read_kb(), 2)
        self.assertEqual(self.query_request.get_max_write_kb(), 3)
        self.assertEqual(self.query_request.get_max_memory_consumption(), 5)
        self.assertEqual(self.query_request.get_math_context(), context)
        self.assertEqual(self.query_request.get_consistency(),
                         Consistency.EVENTUAL)
        self.assertEqual(self.query_request.get_statement(), query_statement)
        self.assertEqual(self.query_request.get_prepared_statement(),
                         self.prepare_result_select.get_prepared_statement())
        self.assertEqual(self.query_request.get_timeout(), timeout)

    def testQueryIllegalRequest(self):
        self.assertRaises(IllegalArgumentException, self.handle.query,
                          'IllegalRequest')

    def testQueryStatementSelect(self):
        num_records = 6
        self.query_request.set_statement(query_statement)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, num_records)
        for idx in range(num_records):
            self.assertEqual(records[idx], self._expected_row(1, idx))
        self.check_cost(result, num_records + prepare_cost,
                        num_records * 2 + prepare_cost, 0, 0)

    def testQueryStatementSelectWithLimit(self):
        limit = 3
        self.query_request.set_statement(query_statement).set_limit(limit)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, limit, True)
        for idx in range(limit):
            self.assertEqual(records[idx], self._expected_row(1, idx))
        self.check_cost(
            result, limit + prepare_cost, limit * 2 + prepare_cost, 0, 0)

    def testQueryStatementSelectWithMaxReadKb(self):
        num_records = 6
        max_read_kb = 4
        self.query_request.set_statement(query_statement).set_max_read_kb(
            max_read_kb)
        result = self.handle.query(self.query_request)
        # TODO: [#27744] KV doesn't honor max read kb for on-prem proxy because
        # it has no table limits.
        if is_onprem():
            records = self.check_query_result(result, num_records)
        else:
            records = self.check_query_result(result, max_read_kb + 1, True)
        for idx in range(len(records)):
            self.assertEqual(records[idx], self._expected_row(1, idx))
        self.check_cost(result, max_read_kb + prepare_cost + 1,
                        max_read_kb * 2 + prepare_cost + 2, 0, 0)

    def testQueryStatementSelectWithConsistency(self):
        num_records = 6
        self.query_request.set_statement(query_statement).set_consistency(
            Consistency.ABSOLUTE)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, num_records)
        for idx in range(num_records):
            self.assertEqual(records[idx], self._expected_row(1, idx))
        self.check_cost(result, num_records + prepare_cost,
                        num_records * 2 + prepare_cost, 0, 0)

    def testQueryStatementSelectWithContinuationKey(self):
        num_records = 6
        limit = 4
        self.query_request.set_statement(query_statement).set_limit(limit)
        count = 0
        while True:
            completed = count * limit
            result = self.handle.query(self.query_request)
            if completed + limit <= num_records:
                num_get = limit
                read_kb = num_get
                records = self.check_query_result(result, num_get, True)
            else:
                num_get = num_records - completed
                read_kb = (1 if num_get == 0 else num_get)
                records = self.check_query_result(result, num_get)
            for idx in range(num_get):
                self.assertEqual(records[idx],
                                 self._expected_row(1, completed + idx))
            self.check_cost(
                result, read_kb + (prepare_cost if count == 0 else 0),
                read_kb * 2 + (prepare_cost if count == 0 else 0), 0, 0)
            count += 1
            if self.query_request.is_done():
                break
        self.assertEqual(count, num_records // limit + 1)

    def testQueryStatementSelectWithDefault(self):
        num_records = 6
        self.query_request.set_statement(
            query_statement).set_defaults(self.handle_config)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, num_records)
        for idx in range(num_records):
            self.assertEqual(records[idx], self._expected_row(1, idx))
        self.check_cost(result, num_records + prepare_cost,
                        num_records * 2 + prepare_cost, 0, 0)

    def testQueryPreparedStatementUpdate(self):
        fld_sid = 0
        fld_id = 2
        fld_long = 2147483649
        prepared_statement = self.prepare_result_update.get_prepared_statement()
        # update a non-existing row
        prepared_statement.set_variable('$fld_sid', 2).set_variable(
            '$fld_id', 0)
        self.query_request.set_prepared_statement(self.prepare_result_update)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'NumRowsUpdated': 0})
        self.check_cost(result, 1, 2, 0, 0)
        # update an existing row
        prepared_statement.set_variable('$fld_sid', fld_sid).set_variable(
            '$fld_id', fld_id)
        self.query_request.set_prepared_statement(self.prepare_result_update)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'NumRowsUpdated': 1})
        self.check_cost(result, 2, 4, 4, 4)
        # check the updated row
        prepared_statement = self.prepare_result_select.get_prepared_statement()
        prepared_statement.set_variable('$fld_long', fld_long)
        self.query_request.set_prepared_statement(prepared_statement)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0],
                         self._expected_row(fld_sid, fld_id, fld_long))
        self.check_cost(result, 1, 2, 0, 0)

    def testQueryPreparedStatementUpdateWithLimit(self):
        fld_sid = 1
        fld_id = 5
        fld_long = 2147483649
        prepared_statement = self.prepare_result_update.get_prepared_statement()
        prepared_statement.set_variable('$fld_sid', fld_sid).set_variable(
            '$fld_id', fld_id)
        self.query_request.set_prepared_statement(
            self.prepare_result_update).set_limit(1)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'NumRowsUpdated': 1})
        self.check_cost(result, 2, 4, 4, 4)
        # check the updated row
        prepared_statement = self.prepare_result_select.get_prepared_statement()
        prepared_statement.set_variable('$fld_long', fld_long)
        self.query_request.set_prepared_statement(prepared_statement)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1, True)
        self.assertEqual(records[0],
                         self._expected_row(fld_sid, fld_id, fld_long))
        self.check_cost(result, 1, 2, 0, 0)

    def testQueryPreparedStatementUpdateWithMaxReadKb(self):
        fld_sid = 0
        fld_id = 1
        fld_long = 2147483649
        # set a small max_read_kb to read a row to update
        prepared_statement = self.prepare_result_update.get_prepared_statement()
        prepared_statement.set_variable('$fld_sid', fld_sid).set_variable(
            '$fld_id', fld_id)
        self.query_request.set_prepared_statement(
            self.prepare_result_update).set_max_read_kb(1)
        if not is_onprem():
            self.assertRaises(IllegalArgumentException, self.handle.query,
                              self.query_request)
        # set a enough max_read_kb to read a row to update
        self.query_request.set_max_read_kb(2)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'NumRowsUpdated': 1})
        self.check_cost(result, 2, 4, 4, 4)
        # check the updated row
        prepared_statement = self.prepare_result_select.get_prepared_statement()
        prepared_statement.set_variable('$fld_long', fld_long)
        self.query_request.set_prepared_statement(prepared_statement)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0],
                         self._expected_row(fld_sid, fld_id, fld_long))
        self.check_cost(result, 1, 2, 0, 0)

    def testQueryPreparedStatementUpdateWithConsistency(self):
        fld_sid = 1
        fld_id = 2
        fld_long = 2147483649
        prepared_statement = self.prepare_result_update.get_prepared_statement()
        prepared_statement.set_variable('$fld_sid', fld_sid).set_variable(
            '$fld_id', fld_id)
        self.query_request.set_prepared_statement(
            self.prepare_result_update).set_consistency(Consistency.ABSOLUTE)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'NumRowsUpdated': 1})
        self.check_cost(result, 2, 4, 4, 4)
        # check the updated row
        prepared_statement = self.prepare_result_select.get_prepared_statement()
        prepared_statement.set_variable('$fld_long', fld_long)
        self.query_request.set_prepared_statement(prepared_statement)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0],
                         self._expected_row(fld_sid, fld_id, fld_long))
        self.check_cost(result, 1, 2, 0, 0)

    def testQueryPreparedStatementUpdateWithContinuationKey(self):
        fld_sid = 1
        fld_id = 3
        fld_long = 2147483649
        num_records = 1
        limit = 3
        prepared_statement = self.prepare_result_update.get_prepared_statement()
        prepared_statement.set_variable('$fld_sid', fld_sid).set_variable(
            '$fld_id', fld_id)
        self.query_request.set_prepared_statement(
            self.prepare_result_update).set_limit(limit)
        count = 0
        while True:
            completed = count * limit
            result = self.handle.query(self.query_request)
            records = self.check_query_result(result, 1)
            if completed + limit <= num_records:
                self.assertEqual(records[0], {'NumRowsUpdated': limit})
                read_kb = limit * 2
                write_kb = limit * 4
            else:
                num_update = num_records - completed
                self.assertEqual(records[0], {'NumRowsUpdated': num_update})
                read_kb = (1 if num_update == 0 else num_update * 2)
                write_kb = (0 if num_update == 0 else num_update * 4)
            self.check_cost(result, read_kb, read_kb * 2, write_kb, write_kb)
            count += 1
            if self.query_request.is_done():
                break
        self.assertEqual(count, 1)
        # check the updated row
        prepared_statement = self.prepare_result_select.get_prepared_statement()
        prepared_statement.set_variable('$fld_long', fld_long)
        self.query_request.set_prepared_statement(prepared_statement)
        result = self.handle.query(self.query_request)
        if limit <= num_records:
            records = self.check_query_result(result, num_records, True)
        else:
            records = self.check_query_result(result, num_records)
        self.assertEqual(records[0],
                         self._expected_row(fld_sid, fld_id, fld_long))
        self.check_cost(result, 1, 2, 0, 0)

    def testQueryPreparedStatementUpdateWithDefault(self):
        fld_sid = 0
        fld_id = 5
        fld_long = 2147483649
        prepared_statement = self.prepare_result_update.get_prepared_statement()
        prepared_statement.set_variable('$fld_sid', fld_sid).set_variable(
            '$fld_id', fld_id)
        self.query_request.set_prepared_statement(
            self.prepare_result_update).set_defaults(self.handle_config)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'NumRowsUpdated': 1})
        self.check_cost(result, 2, 4, 4, 4)
        # check the updated row
        prepared_statement = self.prepare_result_select.get_prepared_statement()
        prepared_statement.set_variable('$fld_long', fld_long)
        self.query_request.set_prepared_statement(prepared_statement)
        result = self.handle.query(self.query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0],
                         self._expected_row(fld_sid, fld_id, fld_long))
        self.check_cost(result, 1, 2, 0, 0)

    def testQueryStatementUpdateTTL(self):
        hour_in_milliseconds = 60 * 60 * 1000
        self.query_request.set_statement(
            'UPDATE ' + table_name + ' $u SET TTL CASE WHEN ' +
            'remaining_hours($u) < 0 THEN 3 ELSE remaining_hours($u) + 3 END ' +
            'HOURS WHERE fld_sid = 1 AND fld_id = 3')
        result = self.handle.query(self.query_request)
        ttl = TimeToLive.of_hours(3)
        expect_expiration = ttl.to_expiration_time(int(round(time() * 1000)))
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'NumRowsUpdated': 1})
        self.check_cost(result, 2 + prepare_cost, 4 + prepare_cost, 6, 6)
        # check the record after update ttl request succeed
        self.get_request.set_key({'fld_sid': 1, 'fld_id': 3})
        result = self.handle.get(self.get_request)
        actual_expiration = result.get_expiration_time()
        actual_expect_diff = actual_expiration - expect_expiration
        self.assertGreater(actual_expiration, 0)
        self.assertLess(actual_expect_diff, hour_in_milliseconds)
        self.check_cost(result, 1, 2, 0, 0)

    def testQueryOrderBy(self):
        num_records = 12
        num_ids = 6
        # test order by primary index field
        statement = ('SELECT fld_sid, fld_id FROM ' + table_name +
                     ' ORDER BY fld_sid, fld_id')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_records, rec=records)
                for idx in range(num_records):
                    self.assertEqual(
                        records[idx],
                        self._expected_row(idx // num_ids, idx % num_ids))
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test order by secondary index field
        statement = ('SELECT fld_str FROM ' + table_name +
                     ' ORDER BY fld_str')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_records, rec=records)
                for idx in range(num_records):
                    self.assertEqual(
                        records[idx],
                        {'fld_str': '{"name": u' + str(idx).zfill(2) + '}'})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    def testQueryFuncMinMaxGroupBy(self):
        num_sids = 2
        # test min function
        statement = ('SELECT min(fld_time) FROM ' + table_name)
        query_request = QueryRequest().set_statement(statement)
        result = self.handle.query(query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'Column_1': self.min_time[0]})
        self.check_cost(result, prepare_cost, prepare_cost, 0, 0, True)

        # test max function
        statement = ('SELECT max(fld_time) FROM ' + table_name)
        query_request = QueryRequest().set_statement(statement)
        result = self.handle.query(query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'Column_1': self.max_time[1]})
        self.check_cost(result, prepare_cost, prepare_cost, 0, 0, True)

        # test min function group by primary index field
        statement = ('SELECT min(fld_time) FROM ' + table_name +
                     ' GROUP BY fld_sid')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx], {'Column_1': self.min_time[idx]})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test max function group by primary index field
        statement = ('SELECT max(fld_time) FROM ' + table_name +
                     ' GROUP BY fld_sid')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx], {'Column_1': self.max_time[idx]})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test min function group by secondary index field
        statement = ('SELECT min(fld_time) FROM ' + table_name +
                     ' GROUP BY fld_bool')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx], {'Column_1': self.min_time[idx]})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

        # test max function group by secondary index field
        statement = ('SELECT max(fld_time) FROM ' + table_name +
                     ' GROUP BY fld_bool')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx], {'Column_1': self.max_time[idx]})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    def testQueryFuncSumGroupBy(self):
        num_records = 12
        num_sids = 2
        # test sum function
        statement = ('SELECT sum(fld_double) FROM ' + table_name)
        query_request = QueryRequest().set_statement(statement)
        result = self.handle.query(query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'Column_1': 3.1415 * num_records})
        self.check_cost(result, prepare_cost, prepare_cost, 0, 0, True)

        # test sum function group by primary index field
        statement = ('SELECT sum(fld_double) FROM ' + table_name +
                     ' GROUP BY fld_sid')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx],
                        {'Column_1': 3.1415 * (num_records // num_sids)})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test sum function group by secondary index field
        statement = ('SELECT sum(fld_double) FROM ' + table_name +
                     ' GROUP BY fld_bool')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx],
                        {'Column_1': 3.1415 * (num_records // num_sids)})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    def testQueryFuncAvgGroupBy(self):
        num_sids = 2
        # test avg function
        statement = ('SELECT avg(fld_double) FROM ' + table_name)
        query_request = QueryRequest().set_statement(statement)
        result = self.handle.query(query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'Column_1': 3.1415})
        self.check_cost(result, prepare_cost, prepare_cost, 0, 0, True)

        # test avg function group by primary index field
        statement = ('SELECT avg(fld_double) FROM ' + table_name +
                     ' GROUP BY fld_sid')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(records[idx], {'Column_1': 3.1415})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test avg function group by secondary index field
        statement = ('SELECT avg(fld_double) FROM ' + table_name +
                     ' GROUP BY fld_bool')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(records[idx], {'Column_1': 3.1415})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    def testQueryFuncCountGroupBy(self):
        num_records = 12
        num_sids = 2
        # test count function
        statement = ('SELECT count(*) FROM ' + table_name)
        query_request = QueryRequest().set_statement(statement)
        result = self.handle.query(query_request)
        records = self.check_query_result(result, 1)
        self.assertEqual(records[0], {'Column_1': num_records})
        self.check_cost(result, prepare_cost, prepare_cost, 0, 0, True)

        # test count function group by primary index field
        statement = ('SELECT count(*) FROM ' + table_name +
                     ' GROUP BY fld_sid')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx], {'Column_1': num_records // num_sids})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test count function group by secondary index field
        statement = ('SELECT count(*) FROM ' + table_name +
                     ' GROUP BY fld_bool')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_sids, rec=records)
                for idx in range(num_sids):
                    self.assertEqual(
                        records[idx], {'Column_1': num_records // num_sids})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    def testQueryOrderByWithLimit(self):
        num_records = 12
        limit = 10
        # test order by primary index field with limit
        statement = ('SELECT fld_str FROM ' + table_name +
                     ' ORDER BY fld_sid, fld_id LIMIT 10')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, limit, rec=records)
                for idx in range(limit):
                    self.assertEqual(
                        records[idx],
                        {'fld_str': '{"name": u' +
                         str(num_records - idx - 1).zfill(2) + '}'})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test order by secondary index field with limit
        statement = ('SELECT fld_str FROM ' + table_name +
                     ' ORDER BY fld_str LIMIT 10')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, limit, rec=records)
                for idx in range(limit):
                    self.assertEqual(
                        records[idx],
                        {'fld_str': '{"name": u' + str(idx).zfill(2) + '}'})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    def testQueryOrderByWithOffset(self):
        offset = 4
        num_get = 8
        # test order by primary index field with offset
        statement = (
            'DECLARE $offset INTEGER; SELECT fld_str FROM ' + table_name +
            ' ORDER BY fld_sid, fld_id OFFSET $offset')
        prepare_request = PrepareRequest().set_statement(statement)
        prepare_result = self.handle.prepare(prepare_request)
        prepared_statement = prepare_result.get_prepared_statement()
        prepared_statement.set_variable('$offset', offset)
        query_request = QueryRequest().set_prepared_statement(
            prepared_statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_get, rec=records)
                for idx in range(num_get):
                    self.assertEqual(
                        records[idx],
                        {'fld_str': '{"name": u' +
                         str(num_get - idx - 1).zfill(2) + '}'})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test order by secondary index field with offset
        statement = (
            'DECLARE $offset INTEGER; SELECT fld_str FROM ' + table_name +
            ' ORDER BY fld_str OFFSET $offset')
        prepare_request = PrepareRequest().set_statement(statement)
        prepare_result = self.handle.prepare(prepare_request)
        prepared_statement = prepare_result.get_prepared_statement()
        prepared_statement.set_variable('$offset', offset)
        query_request = QueryRequest().set_prepared_statement(
            prepared_statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_get, rec=records)
                for idx in range(num_get):
                    self.assertEqual(
                        records[idx], {'fld_str': '{"name": u' +
                                       str(offset + idx).zfill(2) + '}'})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    def testQueryFuncGeoNear(self):
        num_get = 6
        longitude = 21.547
        latitude = 37.291
        # test geo_near function
        statement = (
            'SELECT tb.fld_json.location FROM ' + table_name +
            ' tb WHERE geo_near(tb.fld_json.location, ' +
            '{"type": "point", "coordinates": [' + str(longitude) + ', ' +
            str(latitude) + ']}, 215000)')
        query_request = QueryRequest().set_statement(statement)
        result = self.handle.query(query_request)
        records = self.check_query_result(result, num_get)
        for i in range(1, num_get):
            pre = records[i - 1]['location']['coordinates']
            curr = records[i]['location']['coordinates']
            self.assertLess(abs(pre[0] - longitude),
                            abs(curr[0] - longitude))
            self.assertLess(abs(pre[1] - latitude),
                            abs(curr[1] - latitude))
        self.check_cost(result, prepare_cost, prepare_cost, 0, 0, True)

        # test geo_near function order by primary index field
        statement = (
            'SELECT fld_str FROM ' + table_name + ' tb WHERE geo_near(' +
            'tb.fld_json.location, {"type": "point", "coordinates": [' +
            str(longitude) + ', ' + str(latitude) + ']}, 215000) ' +
            'ORDER BY fld_sid, fld_id')
        query_request = QueryRequest().set_statement(statement)
        count = 0
        while True:
            count += 1
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_get, rec=records)
                name = [10, 9, 8, 4, 3, 2]
                for i in range(num_get):
                    self.assertEqual(
                        records[i], {'fld_str': '{"name": u' +
                                     str(name[i]).zfill(2) + '}'})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)
        self.assertEqual(count, 2)

        # test geo_near function order by secondary index field
        statement = (
            'SELECT fld_str FROM ' + table_name + ' tb WHERE geo_near(' +
            'tb.fld_json.location, {"type": "point", "coordinates": [' +
            str(longitude) + ', ' + str(latitude) + ']}, 215000) ' +
            'ORDER BY fld_str')
        query_request = QueryRequest().set_statement(statement)
        while True:
            result = self.handle.query(query_request)
            records = result.get_results()
            if query_request.is_done():
                self.check_query_result(result, num_get, rec=records)
                name = [2, 3, 4, 8, 9, 10]
                for i in range(num_get):
                    self.assertEqual(
                        records[i], {'fld_str': '{"name": u' +
                                     str(name[i]).zfill(2) + '}'})
                self.check_cost(result, 0, 0, 0, 0)
                break
            else:
                self.check_query_result(result, 0, True, records)
                self.assertEqual(records, [])
                self.check_cost(result, 0, 0, 0, 0, True)

    @staticmethod
    def _expected_row(fld_sid, fld_id, fld_long=None):
        expected_row = OrderedDict()
        expected_row['fld_sid'] = fld_sid
        expected_row['fld_id'] = fld_id
        if fld_long is not None:
            expected_row['fld_long'] = fld_long
        return expected_row


if __name__ == '__main__':
    unittest.main()
