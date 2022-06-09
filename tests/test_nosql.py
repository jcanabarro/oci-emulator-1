import unittest

import oci

from oci.nosql.models import CreateTableDetails, TableLimits
from oci.nosql.models import UpdateRowDetails, QueryDetails

from oci_emulator import app
from . import get_oci_config, ServerThread


def get_nosql_details(ddl_statement, compartment_id):
    table_name = "nosql_invalid_test"

    table_limits = TableLimits(
        max_read_units=1, max_write_units=1, max_storage_in_g_bs=1
    )

    nosql_details = CreateTableDetails(
        name=table_name,
        compartment_id=compartment_id,
        ddl_statement=ddl_statement,
        table_limits=table_limits,
    )
    return nosql_details


class NosqlRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ServerThread(app)
        self.server.start()
        self.oci_config = get_oci_config()
        self.table_name = "nosql_test"
        self.ddl_statement = f"""CREATE TABLE {self.table_name} (first string, second number, third boolean, column4 string DEFAULT "[]" NOT NULL, PRIMARY KEY (first))"""

        table_limits = TableLimits(
            max_read_units=1, max_write_units=1, max_storage_in_g_bs=1
        )

        self.nosql_details = CreateTableDetails(
            name=self.table_name,
            compartment_id=self.oci_config["compartment_id"],
            ddl_statement=self.ddl_statement,
            table_limits=table_limits,
        )

        self.nosql_cli = oci.nosql.NosqlClient(
            self.oci_config["config"], service_endpoint="http://localhost:12000"
        )
        self.nosql_cli.create_table(self.nosql_details)
        response = self.nosql_cli.get_table(
            table_name_or_id=self.table_name,
            compartment_id=self.oci_config["compartment_id"],
        )
        self.table_id = response.data.id

    def test_invalid_creating_table(self):
        table_name = "nosql_invalid_test"

        # missing table details
        nosql_details = get_nosql_details(
            ddl_statement=f"""CREATE TABLE {table_name}""",
            compartment_id=self.oci_config["compartment_id"],
        )
        with self.assertRaises(oci.exceptions.ServiceError):
            self.nosql_cli.create_table(nosql_details)

        # missing primary keys
        nosql_details = get_nosql_details(
            ddl_statement=f"""CREATE TABLE {table_name} ( campo1 string, campo2 string )""",
            compartment_id=self.oci_config["compartment_id"],
        )
        with self.assertRaises(oci.exceptions.ServiceError):
            self.nosql_cli.create_table(nosql_details)

        # missing columns
        nosql_details = get_nosql_details(
            ddl_statement=f"""CREATE TABLE {table_name} ( , PRIMARY KEY ( SHARD ( stream_name ), start ) )""",
            compartment_id=self.oci_config["compartment_id"],
        )
        with self.assertRaises(oci.exceptions.ServiceError):
            self.nosql_cli.create_table(nosql_details)

        # missing column type
        nosql_details = get_nosql_details(
            ddl_statement=f"""CREATE TABLE {table_name} ( campo1 , PRIMARY KEY ( SHARD ( stream_name ), start ) )""",
            compartment_id=self.oci_config["compartment_id"],
        )
        with self.assertRaises(oci.exceptions.ServiceError):
            self.nosql_cli.create_table(nosql_details)

        # invalid column details
        nosql_details = get_nosql_details(
            ddl_statement=f"""CREATE TABLE {table_name} ( campo1 string invalid_details, PRIMARY KEY ( SHARD ( stream_name ), start ) )""",
            compartment_id=self.oci_config["compartment_id"],
        )
        with self.assertRaises(oci.exceptions.ServiceError):
            self.nosql_cli.create_table(nosql_details)

        # invalid primary keys, fields doesnt exist
        nosql_details = get_nosql_details(
            ddl_statement=f"""CREATE TABLE {table_name} ( campo1 string, PRIMARY KEY ( SHARD ( stream_name ), start ) )""",
            compartment_id=self.oci_config["compartment_id"],
        )
        with self.assertRaises(oci.exceptions.ServiceError):
            self.nosql_cli.create_table(nosql_details)

    def test_get_table(self):
        response = self.nosql_cli.get_table(
            table_name_or_id=self.table_name,
            compartment_id=self.oci_config["compartment_id"],
        )
        self.assertEquals(response.data.name, self.table_name)
        self.assertEquals(response.data.ddl_statement, self.ddl_statement)

    def test_get_empty_row(self):
        response = self.nosql_cli.get_table(
            table_name_or_id=self.table_name,
            compartment_id=self.oci_config["compartment_id"],
        )

        nosql_row = UpdateRowDetails()
        nosql_row.value = {"first": "not-value", "second": 1, "third": True}
        self.nosql_cli.update_row(
            table_name_or_id=response.data.id, update_row_details=nosql_row
        )

        response = self.nosql_cli.get_row(
            table_name_or_id=self.table_name,
            compartment_id=self.oci_config["compartment_id"],
            key=["first:value", "second:no-value"],
        )
        self.assertEquals(response.data.value, None)

    def test_get_row_not_key(self):
        nosql_row = UpdateRowDetails()
        nosql_row.value = {"first": "not-value", "second": 1, "third": True}

        self.nosql_cli.update_row(
            table_name_or_id=self.table_id, update_row_details=nosql_row
        )

        response = self.nosql_cli.get_row(
            table_name_or_id=self.table_name,
            compartment_id=self.oci_config["compartment_id"],
            key=["dump:value"],
        )
        self.assertEquals(response.data.value, None)

    def test_create_invalid_row(self):
        nosql_row = UpdateRowDetails()
        nosql_row.value = {"third": True}
        nosql_row.compartment_id = self.oci_config["compartment_id"]

        with self.assertRaises(oci.exceptions.ServiceError):
            self.nosql_cli.update_row(
                table_name_or_id=self.table_name, update_row_details=nosql_row
            )

    def test_create_row_using_name_compartment(self):
        nosql_row = UpdateRowDetails()
        nosql_row.value = {"first": "not-value", "second": 1, "third": True}
        nosql_row.compartment_id = self.oci_config["compartment_id"]
        self.nosql_cli.update_row(
            table_name_or_id=self.table_name, update_row_details=nosql_row
        )

        response = self.nosql_cli.get_row(
            table_name_or_id=self.table_name,
            key=["first:not-value", "second:1"],
            compartment_id=self.oci_config["compartment_id"],
        )
        self.assertEquals(response.data.value["first"], "not-value")
        self.assertEquals(response.data.value["second"], 1)
        self.assertEquals(response.data.value["third"], True)

        query = f"SELECT * FROM {self.table_name} WHERE third = true"
        details = QueryDetails(
            compartment_id=self.oci_config["compartment_id"], statement=query
        )
        response = self.nosql_cli.query(details)
        self.assertEquals(len(response.data.items), 1)

    def test_create_row_using_id(self):
        nosql_row = UpdateRowDetails()
        nosql_row.value = {"first": "value", "second": 0, "third": True}
        self.nosql_cli.update_row(
            table_name_or_id=self.table_id, update_row_details=nosql_row
        )

        response = self.nosql_cli.get_row(
            table_name_or_id=self.table_id, key=["first:value", "second:0"]
        )

        self.assertEquals(response.data.value["first"], "value")
        self.assertEquals(response.data.value["second"], 0)
        self.assertEquals(response.data.value["third"], True)

        query = f"SELECT * FROM {self.table_name} WHERE third = true"
        details = QueryDetails(
            compartment_id=self.oci_config["compartment_id"], statement=query
        )
        response = self.nosql_cli.query(details)
        self.assertEquals(len(response.data.items), 1)

        self.nosql_cli.delete_row(
            table_name_or_id=self.table_id, key=["first:value", "second:0"]
        )

    def test_updating_row_using_id(self):
        nosql_row = UpdateRowDetails()
        nosql_row.value = {"first": "value", "second": 0, "third": True}
        self.nosql_cli.update_row(
            table_name_or_id=self.table_id, update_row_details=nosql_row
        )

        response = self.nosql_cli.get_row(
            table_name_or_id=self.table_id, key=["first:value", "second:0"]
        )

        self.assertEquals(response.data.value["first"], "value")
        self.assertEquals(response.data.value["second"], 0)
        self.assertEquals(response.data.value["third"], True)

        nosql_row = UpdateRowDetails()
        nosql_row.value = {"first": "value", "second": 0, "third": False}
        self.nosql_cli.update_row(
            table_name_or_id=self.table_id, update_row_details=nosql_row
        )

        response = self.nosql_cli.get_row(
            table_name_or_id=self.table_id, key=["first:value", "second:0"]
        )

        self.assertEquals(response.data.value["first"], "value")
        self.assertEquals(response.data.value["second"], 0)
        self.assertEquals(response.data.value["third"], False)

        query = f"SELECT * FROM {self.table_name} WHERE third = true"
        details = QueryDetails(
            compartment_id=self.oci_config["compartment_id"], statement=query
        )
        response = self.nosql_cli.query(details)
        self.assertEquals(len(response.data.items), 1)

        self.nosql_cli.delete_row(
            table_name_or_id=self.table_id, key=["first:value", "second:0"]
        )

    def tearDown(self) -> None:
        self.nosql_cli.delete_table(
            table_name_or_id=self.table_name,
            compartment_id=self.oci_config["compartment_id"],
        )
        self.server.shutdown()
