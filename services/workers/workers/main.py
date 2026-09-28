"""
Worker entrypoint: consumes tasks from Redis Streams (consumer group per
skill), runs the plan stack + DAG batches, compensates via the undo stack on
failure, and escalates to the human queue on unrecoverable failure.

This is a Sprint-0 skeleton; the real consumer loop lands in Sprint 2
alongside the planner and the order-status action.
"""


def main() -> None:
    print("[workers] TODO: connect to Redis Streams and start consuming tasks")


if __name__ == "__main__":
    main()
