import time
from django.db import transaction, IntegrityError
from django.core.cache import cache
from django.utils import timezone

from judge.models import Judgment

RATE_LIMIT = 5  # requests per second
RATE_PERIOD = 1  # seconds

def normalize_and_order(s1: str, s2: str):
    n1 = s1.strip().lower()
    n2 = s2.strip().lower()
    # For symmetry ensure deterministic order
    if n1 <= n2:
        return n1, n2, s1, s2
    else:
        return n2, n1, s2, s1


def save_judgment_concurrent(sentence1: str, sentence2: str,
                             similarity: float, label: str,
                             max_retries: int = 5, backoff: float = 0.02):
    """
    Create or update a Judgment row in a concurrency-safe way.
    Returns the Judgment instance.
    """
    s_norm_a, s_norm_b, s_store_a, s_store_b = normalize_and_order(sentence1, sentence2)

    print(f"Attempting to save: '{s_store_a}', '{s_store_b}' -> {similarity}, {label}")  # Debug

    attempt = 0
    while True:
        attempt += 1
        try:
            with transaction.atomic():
                # Try to create first - will raise IntegrityError if another thread created it
                obj = Judgment.objects.create(
                    sentence1=s_store_a,
                    sentence2=s_store_b,
                    sentence1_norm=s_norm_a,
                    sentence2_norm=s_norm_b,
                    similarity=similarity,
                    label=label,
                )
                print(f"Created new object: {obj.id}")  # Debug
                return obj
        except IntegrityError as e:
            print(f"IntegrityError on attempt {attempt}: {e}")  # Debug
            # Another process created the row concurrently
            # Try to update the existing row deterministically
            try:
                with transaction.atomic():
                    obj = Judgment.objects.select_for_update().get(
                        sentence1_norm=s_norm_a,
                        sentence2_norm=s_norm_b,
                    )
                    print(f"Updating existing object: {obj.id}")  # Debug
                    obj.similarity = similarity
                    obj.label = label
                    obj.save(update_fields=["similarity", "label", "updated_at"])
                    return obj
            except Judgment.DoesNotExist:
                print(f"DoesNotExist on attempt {attempt}")  # Debug
                # Rare: clean up and retry
                pass

        if attempt >= max_retries:
            raise RuntimeError("Could not save judgment after retries due to contention")
        time.sleep(backoff * attempt)



def check_rate_limit(client_ip: str):
    """
    Allow up to RATE_LIMIT requests per RATE_PERIOD seconds per client_ip.
    Uses cache to store timestamps of recent requests.
    """
    key = f"ratelimit:{client_ip}"
    now = timezone.now().timestamp()
    timestamps = cache.get(key, [])
    # Keep only requests in the last RATE_PERIOD seconds
    timestamps = [t for t in timestamps if now - t < RATE_PERIOD]

    if len(timestamps) >= RATE_LIMIT:
        # Too many requests
        return False

    timestamps.append(now)
    cache.set(key, timestamps, timeout=RATE_PERIOD)
    return True
