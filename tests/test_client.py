import logging
import numpy as np
import time
import random
import pytest
import sys

sys.path.append('.')

from faker import Faker

from milvus import IndexType, MetricType, Prepare, Milvus, Status, ParamError, NotConnectError
from milvus.client.abstract import TableSchema, TopKQueryResult
from milvus.client.check import check_pass_param
from milvus.client.hooks import BaseSearchHook

from factorys import (
    table_schema_factory,
    records_factory,
    query_ranges_factory,
    ranges_factory,
    fake
)
from milvus.grpc_gen import milvus_pb2

logging.getLogger('faker').setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)
faker = Faker(locale='en_US')

dim = 128
nb = 2000
nq = 10


class TestConnection:

    def test_true_connect(self, gip):
        cnn = Milvus()

        cnn.connect(*gip)
        assert cnn.status.OK
        assert cnn.connected()

        # Repeating connect
        # _ = cnn.connect(*gip)
        # status = cnn.connect()
        # assert status == Status.CONNECT_FAILED

    # @pytest.mark.skip
    @pytest.mark.parametrize("url", ['tcp://145.98.234.181:9998', 'tcp://199.67.0.1:2'])
    def test_false_connect(self, url):
        cnn = Milvus()
        with pytest.raises(NotConnectError):
            cnn.connect(uri=url, timeout=1)

    # def test_connected(self, gcon):
    #     assert gcon.connected()

    # def test_non_connected(self):
    #     cnn = Milvus()
    #     # import pdb;pdb.set_trace()
    #     assert not cnn.connected()

    def test_uri(self, ghandler, gip):
        cnn = Milvus(handler=ghandler)
        uri = 'tcp://{}:{}'.format(gip[0], gip[1])
        cnn.connect(uri=uri)
        assert cnn.status.OK()

    @pytest.mark.parametrize("url",
                             ['http://127.0.0.1:45678',
                              'tcp://127.0.a.1:9999',
                              'tcp://127.0.0.1:aaa'])
    def test_uri_error(self, url):
        with pytest.raises(Exception):
            cnn = Milvus()
            cnn.connect(uri=url)

    @pytest.mark.parametrize("h", ['12234', 'aaa', '194.16834.200.200', '134.77.89.34'])
    @pytest.mark.parametrize("p", ['...', 'a', '1', '800000'])
    def test_host_port_error(self, h, p):
        with pytest.raises(Exception):
            Milvus().connect(host=h, port=p)

    # def test_disconnected(self, gip):
    #     cnn = Milvus()
    #     cnn.connect(*gip)
    #
    #     assert cnn.disconnect().OK()
    #     assert not cnn.connected()
    #
    #     cnn.connect(*gip)
    #     assert cnn.connected()

    # def test_disconnected_error(self):
    #     cnn = Milvus()
    #     with pytest.raises(NotConnectError):
    #         cnn.disconnect()

    @pytest.mark.skip
    def test_not_connect(self):
        client = Milvus()

        with pytest.raises(NotConnectError):
            client.create_table({})

        with pytest.raises(NotConnectError):
            client.has_table("a")

        with pytest.raises(NotConnectError):
            client.describe_table("a")

        with pytest.raises(NotConnectError):
            client.drop_table("a")

        with pytest.raises(NotConnectError):
            client.create_index("a")

        with pytest.raises(NotConnectError):
            client.insert("a", [], None)

        with pytest.raises(NotConnectError):
            client.count_table("a")

        with pytest.raises(NotConnectError):
            client.show_tables()

        with pytest.raises(NotConnectError):
            client.search("a", 1, 2, [])

        with pytest.raises(NotConnectError):
            client.search_in_files("a", [], [], 2, 1)

        with pytest.raises(NotConnectError):
            client._cmd("")

        with pytest.raises(NotConnectError):
            client.preload_table("a")

        with pytest.raises(NotConnectError):
            client.describe_index("a")

        with pytest.raises(NotConnectError):
            client.drop_index("")


class TestTable:

    def test_create_table(self, gcon):
        param = table_schema_factory()
        param['table_name'] = None
        with pytest.raises(ParamError):
            gcon.create_table(param)

        param = table_schema_factory()
        res = gcon.create_table(param)
        assert res.OK()
        assert gcon.has_table(param['table_name'])

        param = table_schema_factory()
        param['dimension'] = 'string'
        with pytest.raises(ParamError):
            res = gcon.create_table(param)

        param = '09998876565'
        with pytest.raises(ParamError):
            gcon.create_table(param)

        param = table_schema_factory()
        param['table_name'] = 1234456
        with pytest.raises(ParamError):
            gcon.create_table(param)

    def test_create_table_exception(self, gcon):
        param = {
            'table_name': 'test_151314',
            'dimension': 128,
            'index_file_size': 999999
        }

        status = gcon.create_table(param)
        assert not status.OK()

    def test_drop_table(self, gcon, gtable):
        res = gcon.drop_table(gtable)
        assert res.OK()

    def test_false_drop_table(self, gcon):
        table_name = 'fake_table_name'
        res = gcon.drop_table(table_name)
        assert not res.OK()

    def test_repeat_create_table(self, gcon):
        param = table_schema_factory()

        gcon.create_table(param)

        res = gcon.create_table(param)
        LOGGER.error(res)
        assert not res.OK()

    def test_has_table_invalid_name(self, gcon, gtable):
        table_name = "1234455"
        status, result = gcon.has_table(table_name)
        assert not status.OK()


class TestRecordCount:
    def test_count_table(self, gcon, gvector):
        status, num = gcon.count_table(gvector)
        assert status.OK()
        assert num > 0


class TestVector:

    def test_insert(self, gcon, gtable):
        param = {
            'table_name': gtable,
            'records': records_factory(dim, nq)
        }

        res, ids = gcon.insert(**param)
        assert res.OK()
        assert isinstance(ids, list)
        assert len(ids) == nq

    @pytest.mark.skip
    def test_insert_with_numpy(self, gcon, gtable):
        vectors = np.random.rand(nq, dim).astype(np.float32)
        param = {
            'table_name': gtable,
            'records': vectors
        }

        res, ids = gcon.insert(**param)
        assert res.OK()
        assert isinstance(ids, list)
        assert len(ids) == nq

    def test_insert_with_ids(self, gcon, gtable):
        param = {
            'table_name': gtable,
            'records': records_factory(dim, nq),
            'ids': [i + 1 for i in range(nq)]
        }

        res, ids = gcon.insert(**param)
        assert res.OK()
        assert isinstance(ids, list)
        assert len(ids) == nq

    def test_insert_with_wrong_ids(self, gcon, gtable):
        param = {
            'table_name': gtable,
            'records': records_factory(dim, nq),
            'ids': [i + 1 for i in range(nq - 3)]
        }

        with pytest.raises(ParamError):
            gcon.insert(**param)

    def test_insert_with_no_right_dimension(self, gcon, gtable):
        param = {
            'table_name': gtable,
            'records': records_factory(dim + 1, nq)
        }

        res, ids = gcon.insert(**param)
        assert not res.OK()

    def test_insert_records_empty_list(self, gcon, gtable):
        param = {'table_name': gtable, 'records': [[]]}

        with pytest.raises(Exception):
            gcon.insert(**param)

    def test_false_insert(self, gcon):
        param = {
            'table_name': fake.table_name(),
            'records': records_factory(dim, nq)
        }
        res, ids = gcon.insert(**param)
        assert not res.OK()

    def test_insert_wrong_table_name(self, gcon):
        table_name = "&*^%&&dvfdgd(()"

        vectors = records_factory(dim, nq)

        status, _ = gcon.insert(table_name, vectors)
        assert not status.OK()

    # def test_add_vectors_wrong_insert_param(self, gcon, gvector):
    #     vectors = records_factory(dim, nq)
    #
    #     with pytest.raises(ParamError):
    #         gcon.insert(gvector, vectors, insert_param="w353453")


class TestSearch:
    def test_search_normal(self, gcon, gvector):
        topk = random.randint(1, 10)
        query_records = records_factory(dim, nq)
        param = {
            'table_name': gvector,
            'query_records': query_records,
            'top_k': topk,
            'nprobe': 10
        }
        res, results = gcon.search(**param)
        assert res.OK()
        assert len(results) == nq
        assert len(results[0]) == topk

        assert results.shape[0] == nq
        assert results.shape[1] == topk

    def test_search_wrong_dim(self, gcon, gvector):
        topk = random.randint(1, 10)
        query_records = records_factory(dim + 1, nq)
        param = {
            'table_name': gvector,
            'query_records': query_records,
            'top_k': topk,
            'nprobe': 10
        }
        res, results = gcon.search(**param)
        assert not res.OK()

    def test_search_wrong_table_name(self, gcon, gvector):
        topk = random.randint(1, 10)
        query_records = records_factory(dim, nq)
        param = {
            'table_name': gvector + 'wrong',
            'query_records': query_records,
            'top_k': topk,
            'nprobe': 10
        }
        res, _ = gcon.search(**param)
        assert not res.OK()

    def test_false_vector(self, gcon):
        param = {
            'table_name': fake.table_name(),
            'query_records': records_factory(dim, nq),
            'top_k': 'string',
            'nprobe': 10
        }
        with pytest.raises(ParamError):
            gcon.search(**param)

        param = {
            'table_name': fake.table_name(),
            'query_records': records_factory(dim, nq),
            'top_k': 'string',
            'nprobe': 10
        }
        with pytest.raises(ParamError):
            gcon.search(**param)

    def test_search_in_files(self, gcon, gvector):
        param = {
            'table_name': gvector,
            'query_records': records_factory(dim, nq),
            'file_ids': [],
            'top_k': random.randint(1, 10),
            'nprobe': 16
        }

        for id_ in range(5000):
            param['file_ids'].clear()
            param['file_ids'].append(str(id_))
            sta, result = gcon.search_in_files(**param)
            if sta.OK():
                return

        print("search in file failed")
        assert False

    def test_search_in_files_wrong_file_ids(self, gcon, gvector):
        param = {
            'table_name': gvector,
            'query_records': records_factory(dim, nq),
            'file_ids': ['3388833'],
            'top_k': random.randint(1, 10)
        }
        sta, results = gcon.search_in_files(**param)
        assert not sta.OK()

    def test_describe_table(self, gcon, gtable):
        status, table_schema = gcon.describe_table(gtable)
        assert status.OK()
        assert isinstance(table_schema, TableSchema)

    def test_false_decribe_table(self, gcon):
        table_name = fake.table_name()
        res, table_schema = gcon.describe_table(table_name)
        assert not res.OK()
        assert not table_schema

    def test_show_tables(self, gcon, gtable):
        res, tables = gcon.show_tables()
        assert res.OK()
        assert len(tables) == 1

    def test_count_table(self, gcon, gvector, gtable):
        res, count = gcon.count_table(gvector)
        assert res.OK()
        assert count == 10000

    def test_false_count_table(self, gcon):
        res, count = gcon.count_table('fake_table')
        assert not res.OK()

    def test_client_version(self, gcon):
        res = gcon.client_version()
        assert isinstance(res, str)

    def test_server_status(self, gcon):
        status, res = gcon.server_status()
        assert status.OK()


class TestPrepare:

    def test_table_schema(self):
        param = {
            'table_name': fake.table_name(),
            'dimension': random.randint(0, 999),
            'index_file_size': 1024,
            'metric_type': MetricType.L2
        }
        res = Prepare.table_schema(param)
        assert isinstance(res, milvus_pb2.TableSchema)


class TestCreateTable:

    def test_create_table_normal(self, gcon):
        param = table_schema_factory()

        status = gcon.create_table(param)
        assert status.OK()

    def test_create_table_default(self, gcon):
        param = {
            'table_name': 'zilliz_test',
            'dimension': 128
        }

        status = gcon.create_table(param)
        assert status.OK()

        gcon.drop_table('zilliz_test')

    def test_create_table_name_wrong(self, gcon):
        param = table_schema_factory()
        param['table_name'] = '.....'
        status = gcon.create_table(param)
        LOGGER.error(status)
        assert not status.OK()


class TestDescribeTable:

    def test_describe_table_normal(self, gcon):
        param = table_schema_factory()
        gcon.create_table(param)

        status, table = gcon.describe_table(param['table_name'])
        assert status.OK()
        assert table.table_name == param['table_name']

        status, table = gcon.describe_table('table_not_exists')
        assert not status.OK()


class TestShowTables:
    def test_show_tables_normal(self, gcon):
        status, tables = gcon.show_tables()
        LOGGER.error(tables)
        assert status.OK()


class TestDropTable:
    def test_drop_table_normal(self, gcon):
        param = table_schema_factory()
        s = gcon.create_table(param)
        assert s.OK()

        _, tables = gcon.show_tables()
        assert param['table_name'] in tables

        status = gcon.drop_table(param['table_name'])
        _, tables = gcon.show_tables()
        assert param['table_name'] not in tables

    def test_drop_table(self, gcon, gtable):
        status = gcon.drop_table(gtable)
        assert status.OK()


class TestHasTable:
    def test_has_table(self, gcon):
        param = table_schema_factory()
        s = gcon.create_table(param)
        assert s.OK()

        status, flag = gcon.has_table(param['table_name'])
        assert status.OK() and flag


class TestAddVectors:

    def test_insert_normal(self, gcon, gtable):
        vectors = records_factory(dim, nq)
        status, ids = gcon.insert(gtable, vectors)

        assert status.OK()
        assert len(ids) == nq

        status = gcon.flush([gtable])
        assert status.OK(), status.message

        status, count = gcon.count_table(gtable)
        assert status.OK()

        assert count == nq

        gcon.preload_table(gtable)

    def test_insert_numpy_array(self, gcon ,gtable):
        vectors = np.random.rand(10000, 128)
        status, ids = gcon.insert(gtable, vectors)
        assert status.OK(), status.message

    def test_insert_ids(self, gcon, gtable):
        vectors = records_factory(dim, nb)
        ids = [i for i in range(nb)]

        status, vectors_ids = gcon.insert(gtable, vectors, ids)
        assert status.OK()
        assert len(ids) == len(vectors_ids)

        status = gcon.flush([gtable])
        assert status.OK(), status.message

        status, count = gcon.count_table(gtable)
        assert status.OK()

        assert count == nb


class TestIndex:
    @pytest.mark.skip(reason="hnsw in not supported on crud branch")
    def test_available_index(self, gcon, gtable):
        for name, member in IndexType.__members__.items():
            if member.value == 0:
                continue

            _index = {
                'index_type': member,
                'nlist': 4096
            }
            print("Index {}".format(member))
            status = gcon.create_index(gtable, _index)
            assert status.OK(), "Index {} create failed: {}".format(member, status.message)

            gcon.drop_index(gtable)

    def test_describe_index(self, gcon, gtable):
        vectors = records_factory(dim, nb)
        status, ids = gcon.insert(gtable, vectors)

        assert status.OK()
        assert len(ids) == nb

        status = gcon.flush([gtable])
        assert status.OK(), status.message

        _index = {
            'index_type': IndexType.IVFLAT,
            'nlist': 4096
        }

        status = gcon.create_index(gtable, _index)
        assert status.OK(), status.message

        status, index_schema = gcon.describe_index(gtable)

        assert status.OK()
        print("\n{}\n".format(index_schema))

    def test_describe_index_wrong_table_name(self, gcon):
        table_name = "%&%&"
        status, _ = gcon.describe_index(table_name)

        assert not status.OK()

    def test_drop_index(self, gcon, gtable):
        vectors = records_factory(dim, nb)
        status, ids = gcon.insert(gtable, vectors)

        assert status.OK()
        assert len(ids) == nb

        status = gcon.flush([gtable])
        assert status.OK(), status.message

        status, count = gcon.count_table(gtable)
        assert status.OK()
        assert count == nb

        _index = {
            'index_type': IndexType.IVFLAT,
            'nlist': 16384
        }

        status = gcon.create_index(gtable, _index)
        assert status.OK()

        status = gcon.drop_index(gtable)
        assert status.OK()


@pytest.mark.skip(reason="crud branch")
class TestSearchByID:
    def test_search_by_id_normal(self, gcon, gtable):
        vectors = records_factory(dim, nq)
        status, ids = gcon.insert(gtable, vectors)

        assert status.OK()

        status = gcon.flush([gtable])
        assert status.OK(), status.message

        status, result = gcon.search_by_id(gtable, 2, 10, ids[0])
        assert status.OK()

        print(result)

        assert 1 == len(result)
        assert 2 == len(result[0])
        assert ids[0] == result[0][0].id

    def test_search_by_id_with_partitions(self, gcon, gtable):
        tag = "search_by_id_partitions_tag"

        status = gcon.create_partition(gtable, tag)
        assert status.OK()

        vectors = records_factory(dim, nq)
        status, ids = gcon.insert(gtable, vectors, partition_tag=tag)
        assert status.OK()

        time.sleep(2)

        status, result = gcon.search_by_id(gtable, 2, 10, ids[0], partition_tag_array=[tag])
        assert status.OK()

        assert 1 == len(result)
        assert 2 == len(result[0])
        assert ids[0] == result[0][0].id

    def test_search_by_id_with_wrong_param(self, gcon, gtable):
        with pytest.raises(ParamError):
            gcon.search_by_id(gtable, 'x', 1, 1)

        with pytest.raises(ParamError):
            gcon.search_by_id(gtable, 1, '1', 1)

        with pytest.raises(ParamError):
            gcon.search_by_id(gtable, 1, 1, 'aaa')

        status, _ = gcon.search_by_id(gtable, -1, 1, 1)
        assert not status.OK()

        status, _ = gcon.search_by_id(gtable, 1, -1, 1)
        assert not status.OK()

    @pytest.mark.skip(reason="except empty result, return result with -1 id instead")
    def test_search_by_id_with_exceed_id(self, gcon, gtable):
        vectors = records_factory(dim, nq)
        status, ids = gcon.insert(gtable, vectors)
        assert status.OK()

        status, result = gcon.search_by_id(gtable, 2, 10, ids[0] + 100)
        assert status.OK()
        print(result)
        assert 0 == len(result)


class TestBuildIndex:
    def test_build_index(self, gcon, gvector):
        _D = 128

        time.sleep(5)

        _index = {
            'index_type': IndexType.IVFLAT,
            'nlist': 4096
        }

        print("Create index ... ")
        status = gcon.create_index(gvector, _index)
        assert status.OK()

    def test_create_index_wrong_index(self, gcon, gvector):
        _index = "23523423"

        with pytest.raises(ParamError):
            gcon.create_index(gvector, _index)

    def test_create_index_wrong_table_name(self, gcon, gvector):
        _index = {
            'index_type': IndexType.IVFLAT,
            'nlist': 4096
        }

        status = gcon.create_index("*^&*^dtedge", timeout=-1)
        assert not status.OK()


class TestCmd:
    versions = ("0.5.3", "0.6.0", "0.7.0")

    def test_client_version(self, gcon):
        try:
            import milvus
            assert gcon.client_version() == milvus.__version__
        except ImportError:
            assert False, "Import error"

    def test_server_version(self, gcon):
        _, version = gcon.server_version()
        assert version in self.versions

    def test_server_status(self, gcon):
        _, status = gcon.server_status()
        assert status in ("OK", "ok")

    def test_cmd(self, gcon):
        _, info = gcon._cmd("version")
        assert info in self.versions

        _, info = gcon._cmd("status")
        assert info in ("OK", "ok")


class TestChecking:

    @pytest.mark.parametrize(
        "key_, value_",
        [("ids", [1, 2]), ("nprobe", 12), ("nlist", 4096), ("cmd", 'OK')]
    )
    def test_param_check_normal(self, key_, value_):
        try:
            check_pass_param(**{key_: value_})
        except Exception:
            assert False

    @pytest.mark.parametrize(
        "key_, value_",
        [("ids", []), ("nprobe", "aaa"), ("nlist", "aaa"), ("cmd", 123)]
    )
    def test_param_check_error(self, key_, value_):
        with pytest.raises(ParamError):
            check_pass_param(**{key_: value_})


class TestQueryResult:
    query_vectors = [[random.random() for _ in range(128)] for _ in range(200)]

    def _get_response(self, gcon, gvector, topk, nprobe, nq):
        return gcon.search(gvector, topk, nprobe, self.query_vectors[:nq])

    def test_search_result(self, gcon, gvector):
        try:
            status, results = self._get_response(gcon, gvector, 2, 2, 1)
            assert status.OK()

            # test get_item
            shape = results.shape

            # test TopKQueryResult slice
            rows = results[:1]

            # test RowQueryResult
            row = results[shape[0] - 1]

            # test RowQueryResult slice
            items = row[:1]

            # test iter
            for topk_result in results:
                for item in topk_result:
                    print(item)

            # test len
            len(results)
            # test print
            print(results)

            # test result for nq = 10, topk = 10
            status, results = self._get_response(gcon, gvector, 10, 10, 10)
            print(results)
        except Exception:
            assert False

    def test_search_in_files_result(self, gcon, gvector):
        try:
            for index in range(1000):
                status, results = \
                    gcon.search_in_files(table_name=gvector, top_k=1, nprobe=1,
                                         file_ids=[str(index)], query_records=self.query_vectors)
                if status.OK():
                    break

            # test get_item
            shape = results.shape
            item = results[shape[0] - 1][shape[1] - 1]

            # test iter
            for topk_result in results:
                for item in topk_result:
                    print(item)

            # test len
            len(results)
            # test print
            print(results)
        except Exception:
            assert False

    def test_empty_result(self, gcon, gtable):
        status, results = self._get_response(gcon, gtable, 3, 3, 3)
        shape = results.shape

        for topk_result in results:
            for item in topk_result:
                print(item)


class TestPartition:

    def test_create_partition_in_empty_table(self, gcon, gtable):
        status = gcon.create_partition(table_name=gtable, partition_tag="1")
        assert status.OK()

        vectors = [[random.random() for _ in range(128)] for _ in range(100)]
        status, _ = gcon.insert(gtable, vectors, partition_tag="1")
        assert status.OK()

    def test_create_partition_after_insert(self, gcon, gvector):
        status = gcon.create_partition(table_name=gvector, partition_tag="1")
        assert status.OK()

    def test_insert_with_wrong_partition(self, gcon, gtable):
        status = gcon.create_partition(table_name=gtable, partition_tag="1")
        assert status.OK()

        vectors = [[random.random() for _ in range(128)] for _ in range(100)]
        status, _ = gcon.insert(gtable, vectors, partition_tag="2")
        assert not status.OK()

    def test_search_with_partition_first(self, gcon, gtable):
        status = gcon.create_partition(table_name=gtable, partition_tag="2")
        assert status.OK()

        status, partitions = gcon.show_partitions(gtable)
        assert status.OK()

        vectors = [[random.random() for _ in range(128)] for _ in range(100)]
        status, ids = gcon.insert(gtable, vectors, partition_tag="2")
        assert status.OK()
        assert len(ids) == 100

        time.sleep(5)

        query_vectors = vectors[:1]

        # search in global scope
        status, results = gcon.search(gtable, 1, 1, query_vectors)
        assert status.OK()
        assert results.shape == (1, 1)

        # search in specific tags
        status, results = gcon.search(gtable, 1, 1, query_vectors, partition_tags=["2"])
        assert status.OK()
        assert results.shape == (1, 1)

        # search in non-existing tags
        status, results = gcon.search(
            gtable, 1, 1,
            query_vectors,
            partition_tags=["ee4tergdgdgedgdgergete5465efdf"])

        assert status.OK()
        print(results)
        assert results.shape == (0, 0)

    # @pytest.mark.skip
    def test_search_with_partition_insert_first(self, gcon, gtable):
        vectors = [[random.random() for _ in range(128)] for _ in range(100)]
        status, ids = gcon.insert(gtable, vectors)
        assert status.OK()
        assert len(ids) == 100

        # waiting for data prepared
        time.sleep(5)

        partition_tag = "partition_tag_" + faker.word()

        status = gcon.create_partition(table_name=gtable, partition_tag=partition_tag)
        assert status.OK()

        status, partitions = gcon.show_partitions(gtable)
        assert status.OK()

        query_vectors = [[random.random() for _ in range(128)] for _ in range(1)]

        # search in global scope
        status, results = gcon.search(gtable, 1, 1, query_vectors)
        assert status.OK()
        assert results.shape == (1, 1)

        # search in specific tags
        status, results = gcon.search(gtable, 1, 1, query_vectors, partition_tags=[partition_tag])
        assert status.OK()
        print(results)
        assert results.shape == (0, 0)

        # search in wrong tags
        status, results = gcon.search(gtable, 1, 1, query_vectors, partition_tags=[faker.word() + "wrong"])
        assert status.OK(), status.message
        print(results)
        assert results.shape == (0, 0)

    def test_drop_partition(self, gcon, gtable):
        status = gcon.create_partition(gtable, "1")
        assert status.OK()

        vectors = [[random.random() for _ in range(128)] for _ in range(100)]
        status, _ = gcon.insert(gtable, vectors, partition_tag="1")
        assert status.OK()

        status = gcon.drop_partition(gtable, "1")
        assert status.OK(), status.message


class TestSegment:
    def test_table_info(self, gcon, gvector):
        status, info = gcon.table_info(gvector)
        assert status.OK(), status.message
        assert info.count == 10000
        assert isinstance(info.partitions_stat, list)

        par0 = info.partitions_stat[0]
        assert par0.tag == "_default"
        assert isinstance(par0.segments_stat, list)

        print(info)

    def test_table_info_wrong_name(self, gcon):
        status, _ = gcon.table_info("124124122****")
        assert not status.OK()

    def test_get_segment_ids(self, gcon, gvector):
        status, info = gcon.table_info(gvector)
        assert status.OK()

        seg0 = info.partitions_stat[0].segments_stat[0]

        status, ids = gcon.get_vector_ids(gvector, seg0.segment_name)
        assert status.OK(), status.message
        print(ids[:5])

    def test_get_segment_invalid_ids(self, gcon):
        with pytest.raises(ParamError):
            gcon.get_vector_ids(123, "")

        with pytest.raises(ParamError):
            gcon.get_vector_ids("111", [])

    def test_get_segment_non_existent_table_segment(self, gcon, gtable):
        status, _ = gcon.get_vector_ids("ijojojononsfsfswgsw", "aaa")
        assert not status.OK()

        status, _ = gcon.get_vector_ids(gtable, "aaaaaa")
        assert not status.OK()


class TestGetVectorByID:
    def test_get_vector_by_id(self, gcon, gtable):

        vectors = records_factory(128, 1000)
        ids = [i for i in range(1000)]
        status, ids_out = gcon.insert(table_name=gtable, records=vectors, ids=ids)
        assert status.OK(), status.message

        gcon.flush([gtable])

        status, vec = gcon.get_vector_by_id(gtable, ids_out[0])
        assert status.OK()


class TestDeleteByID:
    def test_delete_by_id_normal(self, gcon, gtable):
        vectors = records_factory(dim, nq)
        status, ids = gcon.insert(gtable, vectors)
        assert status.OK()

        time.sleep(2)

        status = gcon.delete_by_id(gtable, ids[0:10])
        assert status.OK()

    def test_delete_by_id_wrong_param(self, gcon, gtable):
        with pytest.raises(ParamError):
            gcon.delete_by_id(gtable, "aaa")

    @pytest.mark.skip
    def test_delete_by_id_succeed_id(self, gcon, gtable):
        vectors = records_factory(dim, nq)
        status, ids = gcon.insert(gtable, vectors)
        assert status.OK()

        time.sleep(2)

        ids_exceed = [ids[-1] + 10]
        status = gcon.delete_by_id(gtable, ids_exceed)
        assert not status.OK()


class TestFlush:
    def test_flush(self, gcon):
        table_param = {
            "table_name": '',
            "dimension": dim
        }

        table_list = ["test_flush_1", "test_flush_2", "test_flush_3"]
        vectors = records_factory(dim, nq)
        for table in table_list:
            table_param["table_name"] = table

            gcon.create_table(table_param)

            gcon.insert(table, vectors)

        status = gcon.flush(table_list)
        assert status.OK()

        for table in table_list:
            gcon.drop_table(table)

    def test_flush_with_none(self, gcon, gtable):
        table_param = {
            "table_name": '',
            "dimension": dim
        }

        table_list = ["test_flush_1", "test_flush_2", "test_flush_3"]
        vectors = records_factory(dim, nq)
        for table in table_list:
            table_param["table_name"] = table

            gcon.create_table(table_param)

            gcon.insert(table, vectors)

        status = gcon.flush()
        assert status.OK(), status.message

        for table in table_list:
            gcon.drop_table(table)


class TestCompact:
    def test_compact_normal(self, gcon, gtable):
        vectors = [[random.random() for _ in range(128)] for _ in range(10000)]
        status, ids = gcon.add_vectors(table_name=gtable, records=vectors)
        assert status.OK()

        status = gcon.compact(gtable)
        assert status.OK(), status.message

    def test_compact_after_delete(self, gcon, gtable):
        vectors = [[random.random() for _ in range(128)] for _ in range(10000)]
        status, ids = gcon.insert(table_name=gtable, records=vectors)
        assert status.OK(), status.message

        status = gcon.flush([gtable])
        assert status.OK(), status.message

        status = gcon.delete_by_id(gtable, ids[100:1000])
        assert status, status.message

        status = gcon.compact(gtable)
        assert status.OK(), status.message

    def test_compact_with_empty_table(self, gcon, gtable):
        status = gcon.compact(gtable)
        assert status.OK(), status.message

    def test_compact_with_non_exist_name(self, gcon):
        status = gcon.compact(table_name="die333")
        assert not status.OK()

    def test_compact_with_invalid_name(self, gcon):
        with pytest.raises(ParamError):
            gcon.compact(table_name=124)


class TestTableInfo:
    def test_table_info_normal(self, gcon, gtable):
        for _ in range(10):
            records = records_factory(128, 10000)
            status, _ = gcon.insert(gtable, records)
            assert status.OK()

        gcon.flush([gtable])

        status, _ = gcon.table_info(gtable, timeout=None)
        assert status.OK()

    def test_table_info_with_partitions(self, gcon, gtable):
        for i in range(5):
            partition_tag = "tag_{}".format(i)

            status = gcon.create_partition(gtable, partition_tag)
            assert status.OK(), status.message

            for j in range(3):
                records = records_factory(128, 10000)
                status, _ = gcon.insert(gtable, records, partition_tag=partition_tag)
                assert status.OK(), status.message

        status = gcon.flush([gtable])
        assert status.OK(), status.message

        status, _ = gcon.table_info(gtable, timeout=None)
        assert status.OK(), status.message

    def test_table_info_with_empty_table(self, gcon, gtable):
        status, _ = gcon.table_info(gtable)

        assert status.OK(), status.message

    def test_table_info_with_non_exist_table(self, gcon):
        status, _ = gcon.table_info("Xiaxiede")
        assert not status.OK(), status.message
