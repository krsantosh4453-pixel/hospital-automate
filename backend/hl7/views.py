"""
HL7 v2 Messaging Views for Hospital Management System.

Provides HL7 v2 message receiving and processing endpoints.
"""

from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)


# ============================================================
# HL7 Message Processing
# ============================================================

@method_decorator(csrf_exempt, name='dispatch')
class HL7MessageView(APIView):
    """Base HL7 message handler."""

    permission_classes = [AllowAny]  # HL7 typically uses MLLP, not HTTP auth

    def parse_hl7_message(self, message: str):
        """Parse HL7 message into segments."""
        segments = message.strip().split('\r')
        parsed = {}
        for segment in segments:
            if segment:
                fields = segment.split('|')
                segment_name = fields[0] if fields else ''
                parsed.setdefault(segment_name, []).append(fields)
        return parsed

    def build_ack(self, msh_segment, ack_code='AA', error_message=''):
        """Build HL7 ACK message."""
        # MSH|^~\\&|RECEIVER|FACILITY|SENDER|FACILITY|DATETIME||ACK|MSGID|P|2.5
        # MSA|ACKCODE|MSGID|ERROR
        msh_fields = msh_segment.split('|')
        sending_app = msh_fields[2] if len(msh_fields) > 2 else 'UNKNOWN'
        sending_facility = msh_fields[3] if len(msh_fields) > 3 else 'UNKNOWN'
        receiving_app = msh_fields[4] if len(msh_fields) > 4 else 'HMS'
        receiving_facility = msh_fields[5] if len(msh_fields) > 5 else 'HOSPITAL'
        msg_id = msh_fields[9] if len(msh_fields) > 9 else '1'

        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        ack = f"MSH|^~\\&|{receiving_app}|{receiving_facility}|{sending_app}|{sending_facility}|{timestamp}||ACK^{ack_code}|{msg_id}|P|2.5\r"
        ack += f"MSA|{ack_code}|{msg_id}"
        if error_message:
            ack += f"|{error_message}"
        ack += "\r"

        return ack


@method_decorator(csrf_exempt, name='dispatch')
class ADTEndpointView(HL7MessageView):
    """ADT (Admit/Discharge/Transfer) message endpoint."""

    def post(self, request):
        try:
            message = request.body.decode('utf-8')
            logger.info(f"Received ADT message: {message[:200]}")

            parsed = self.parse_hl7_message(message)
            msh = parsed.get('MSH', [['']])[0]
            msh_str = '|'.join(msh) if msh else ''

            # Process based on message type (MSH-9)
            msg_type = msh[8] if len(msh) > 8 else ''
            if '^' in msg_type:
                event_type = msg_type.split('^')[1]
            else:
                event_type = msg_type

            # TODO: Process ADT events (A01-A60)
            # A01 - Admit, A03 - Discharge, A04 - Register, etc.

            ack = self.build_ack(msh_str, 'AA')
            return HttpResponse(ack, content_type='application/hl7-v2')

        except Exception as e:
            logger.exception("ADT processing error")
            return HttpResponse(
                self.build_ack('', 'AE', str(e)),
                content_type='application/hl7-v2',
                status=500
            )


@method_decorator(csrf_exempt, name='dispatch')
class ORMEndpointView(HL7MessageView):
    """ORM (Order Entry) message endpoint."""

    def post(self, request):
        try:
            message = request.body.decode('utf-8')
            logger.info(f"Received ORM message: {message[:200]}")

            parsed = self.parse_hl7_message(message)
            msh = parsed.get('MSH', [['']])[0]
            msh_str = '|'.join(msh) if msh else ''

            # TODO: Process order messages (O01, O02, etc.)

            ack = self.build_ack(msh_str, 'AA')
            return HttpResponse(ack, content_type='application/hl7-v2')

        except Exception as e:
            logger.exception("ORM processing error")
            return HttpResponse(
                self.build_ack('', 'AE', str(e)),
                content_type='application/hl7-v2',
                status=500
            )


@method_decorator(csrf_exempt, name='dispatch')
class ORUEndpointView(HL7MessageView):
    """ORU (Observation Result) message endpoint."""

    def post(self, request):
        try:
            message = request.body.decode('utf-8')
            logger.info(f"Received ORU message: {message[:200]}")

            parsed = self.parse_hl7_message(message)
            msh = parsed.get('MSH', [['']])[0]
            msh_str = '|'.join(msh) if msh else ''

            # TODO: Process lab results (R01, R03, etc.)

            ack = self.build_ack(msh_str, 'AA')
            return HttpResponse(ack, content_type='application/hl7-v2')

        except Exception as e:
            logger.exception("ORU processing error")
            return HttpResponse(
                self.build_ack('', 'AE', str(e)),
                content_type='application/hl7-v2',
                status=500
            )


@method_decorator(csrf_exempt, name='dispatch')
class MFNEndpointView(HL7MessageView):
    """MFN (Master File Notification) message endpoint."""

    def post(self, request):
        try:
            message = request.body.decode('utf-8')
            logger.info(f"Received MFN message: {message[:200]}")

            parsed = self.parse_hl7_message(message)
            msh = parsed.get('MSH', [['']])[0]
            msh_str = '|'.join(msh) if msh else ''

            # TODO: Process master file updates

            ack = self.build_ack(msh_str, 'AA')
            return HttpResponse(ack, content_type='application/hl7-v2')

        except Exception as e:
            logger.exception("MFN processing error")
            return HttpResponse(
                self.build_ack('', 'AE', str(e)),
                content_type='application/hl7-v2',
                status=500
            )


# Function-based views for URL routing
adt_endpoint = ADTEndpointView.as_view()
orm_endpoint = ORMEndpointView.as_view()
oru_endpoint = ORUEndpointView.as_view()
mfn_endpoint = MFNEndpointView.as_view()


@method_decorator(csrf_exempt, name='dispatch')
class GenericHL7View(HL7MessageView):
    """Generic HL7 message endpoint."""

    def post(self, request):
        try:
            message = request.body.decode('utf-8')
            logger.info(f"Received HL7 message: {message[:200]}")

            parsed = self.parse_hl7_message(message)
            msh = parsed.get('MSH', [['']])[0]
            msh_str = '|'.join(msh) if msh else ''

            ack = self.build_ack(msh_str, 'AA')
            return HttpResponse(ack, content_type='application/hl7-v2')

        except Exception as e:
            logger.exception("HL7 processing error")
            return HttpResponse(
                self.build_ack('', 'AE', str(e)),
                content_type='application/hl7-v2',
                status=500
            )


hl7_message_endpoint = GenericHL7View.as_view()


def acknowledgment(request, message_id):
    """Get acknowledgment status for a message."""
    return Response({'message_id': message_id, 'status': 'acknowledged'})


def hl7_status(request):
    """HL7 interface status."""
    return Response({
        'status': 'active',
        'version': '2.5.1',
        'supported_messages': ['ADT', 'ORM', 'ORU', 'MFN'],
    })