from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from judge.services.judge import judge_pair, judge_bulk_pairs
from judge.services.utils import check_rate_limit

class JudgeView(APIView):
    """POST /judge — single pair"""

    def post(self, request):
        client_ip = request.META.get("REMOTE_ADDR", "unknown")

        if not check_rate_limit(client_ip):
            return Response(
                {"error": "Rate limit exceeded. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        s1 = request.data.get("sentence1")
        s2 = request.data.get("sentence2")
        if not s1 or not s2:
            return Response(
                {"error": "Both 'sentence1' and 'sentence2' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = judge_pair(s1, s2)
        return Response(result)


class BulkJudgeView(APIView):
    """POST /judge/bulk — up to 100 pairs"""

    def post(self, request):
        client_ip = request.META.get("REMOTE_ADDR", "unknown")

        if not check_rate_limit(client_ip):
            return Response(
                {"error": "Rate limit exceeded. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        pairs = request.data.get("pairs")
        if not pairs or not isinstance(pairs, list):
            return Response(
                {"error": "Expected 'pairs' to be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(pairs) > 100:
            return Response(
                {"error": "Maximum 100 pairs allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use the efficient batch version
        results = judge_bulk_pairs(pairs)

        return Response(results)
