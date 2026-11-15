"""The OpenAPI schema describes the endpoints the mobile client is generated from (Phase 2)."""

from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator


class MobileSchemaTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = SchemaGenerator().get_schema(request=None, public=True)

    def component(self, name):
        return self.schema["components"]["schemas"][name]["properties"]

    def test_booking_documents_the_retry_header_and_conflict(self):
        book = self.schema["paths"]["/api/v1/appointments/book/"]["post"]

        headers = {p["name"]: p for p in book["parameters"] if p["in"] == "header"}
        self.assertIn("Idempotency-Key", headers)
        self.assertFalse(headers["Idempotency-Key"].get("required", False))
        self.assertTrue({"200", "201", "400", "409"} <= set(book["responses"]))
        self.assertIn("appointment_time", self.component("BookingRequest"))

    def test_booking_options_document_slot_capacity(self):
        self.assertEqual(set(self.component("BookingSlot")), {"time", "available", "capacity", "remaining"})

    def test_slot_place_and_capacity_are_documented(self):
        self.assertTrue(self.component("Appointment")["slot_seat"].get("readOnly"))
        capacity = self.component("Doctor")["slot_capacity"]
        self.assertEqual((capacity["minimum"], capacity["maximum"]), (1, 20))

    def test_computed_fields_used_by_the_mobile_app_have_real_types(self):
        self.assertEqual(self.component("Invoice")["is_paid"]["type"], "boolean")
        self.assertEqual(self.component("Invoice")["balance_due"]["type"], "string")
        self.assertEqual(self.component("Hospital")["doctors"]["type"], "integer")
        self.assertEqual(self.component("Department")["doctors"]["type"], "integer")
        self.assertEqual(self.component("QueueToken")["waiting_minutes"]["type"], "integer")
