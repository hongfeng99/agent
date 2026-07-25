import json

import requests


BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    """
    创建后台研究任务，并实时打印 SSE 事件。
    """

    topic = (
        "MCP 协议对智能体开发有什么价值？"
    )

    create_response = requests.post(
        f"{BASE_URL}/research/tasks",
        json={
            "topic": topic,
        },
        timeout=30,
    )

    create_response.raise_for_status()

    create_data = create_response.json()

    job_id = create_data["job_id"]

    print("=" * 70)
    print("后台研究任务已创建")
    print("=" * 70)
    print(f"研究主题：{topic}")
    print(f"任务编号：{job_id}")
    print()
    print("正在订阅研究事件……")

    event_url = (
        f"{BASE_URL}/research/tasks/"
        f"{job_id}/events"
    )

    with requests.get(
        event_url,
        stream=True,
        timeout=600,
    ) as response:
        response.raise_for_status()

        event_type = "message"
        data_lines: list[str] = []

        for line in response.iter_lines(
            decode_unicode=True
        ):
            if line is None:
                continue

            if line == "":
                if data_lines:
                    payload_text = "\n".join(
                        data_lines
                    )

                    payload = json.loads(
                        payload_text
                    )

                    print()
                    print(
                        f"[{event_type}] "
                        f"{payload['message']}"
                    )

                    event_data = payload.get(
                        "data",
                        {},
                    )

                    if event_data:
                        print(
                            json.dumps(
                                event_data,
                                ensure_ascii=False,
                                indent=2,
                            )
                        )

                event_type = "message"
                data_lines = []
                continue

            if line.startswith(":"):
                continue

            if line.startswith("event:"):
                event_type = (
                    line.split(
                        ":",
                        maxsplit=1,
                    )[1].strip()
                )
                continue

            if line.startswith("data:"):
                data_lines.append(
                    line.split(
                        ":",
                        maxsplit=1,
                    )[1].strip()
                )

    status_response = requests.get(
        f"{BASE_URL}/research/tasks/{job_id}",
        timeout=30,
    )

    status_response.raise_for_status()

    job_data = status_response.json()

    print()
    print("=" * 70)
    print("后台研究任务最终状态")
    print("=" * 70)
    print(f"状态：{job_data['status']}")
    print(f"进度：{job_data['progress']}%")
    print(
        f"报告路径："
        f"{job_data['report_path']}"
    )


if __name__ == "__main__":
    main()