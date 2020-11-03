import os
from unittest.mock import Mock, patch

from dask_pytorch.dispatch import run, dispatch_with_ddp
import dask.distributed


workers = {
    "tcp://1.2.3.4:8786": {"host": "1.2.3.4"},
    "tcp://2.2.3.4:8786": {"host": "2.2.3.4"},
    "tcp://3.2.3.4:8786": {"host": "3.2.3.4"},
    "tcp://4.2.3.4:8786": {"host": "4.2.3.4"},
}
host_name = sorted(workers.keys())[0]
host = workers[host_name]["host"]


def test_run():
    client = Mock()
    client.scheduler_info = Mock(return_value={"workers": workers})

    fake_pytorch_func = Mock()

    fake_results = []
    for idx, worker in enumerate(sorted(workers.keys())):
        r = Mock()
        r.result = Mock(return_value=idx)
        fake_results.append(r)

    client.submit = Mock(side_effect=fake_results)

    with patch("dask_pytorch.dispatch.as_completed", return_value=fake_results) as as_completed:
        as_completed.return_value = fake_results
        output = run(client, fake_pytorch_func)

    client.submit.assert_any_call(
        dispatch_with_ddp, fake_pytorch_func, host, 23456, 0, len(workers)
    )
    client.submit.assert_any_call(
        dispatch_with_ddp, fake_pytorch_func, host, 23456, 1, len(workers)
    )
    client.submit.assert_any_call(
        dispatch_with_ddp, fake_pytorch_func, host, 23456, 2, len(workers)
    )
    client.submit.assert_any_call(
        dispatch_with_ddp, fake_pytorch_func, host, 23456, 3, len(workers)
    )
    assert output == [x.result() for x in fake_results]


def test_run_async():
    client = Mock()
    client.scheduler_info = Mock(return_value={"workers": workers})

    fake_pytorch_func = Mock()

    fake_results = []
    for idx, worker in enumerate(sorted(workers.keys())):
        r = Mock()
        r.result = Mock(return_value=idx)
        fake_results.append(r)

    client.submit = Mock(side_effect=fake_results)

    with patch("dask_pytorch.dispatch.as_completed", return_value=fake_results) as as_completed:
        as_completed.return_value = fake_results
        output = run(client, fake_pytorch_func, sync=False)

    client.submit.assert_any_call(
        dispatch_with_ddp,
        fake_pytorch_func,
        host,
        23456,
        0,
        len(workers),
    )
    client.submit.assert_any_call(
        dispatch_with_ddp, fake_pytorch_func, host, 23456, 1, len(workers)
    )
    client.submit.assert_any_call(
        dispatch_with_ddp, fake_pytorch_func, host, 23456, 2, len(workers)
    )
    client.submit.assert_any_call(
        dispatch_with_ddp, fake_pytorch_func, host, 23456, 3, len(workers)
    )
    assert output == fake_results


def test_dispatch_with_ddp():
    pytorch_func = Mock()

    with patch.object(os, "environ", {}) as environ, patch(
        "dask_pytorch.dispatch.dist", return_value=Mock()
    ) as dist:
        dispatch_with_ddp(pytorch_func, "master_addr", 2343, 1, 10, "a", "b", foo="bar")
        assert environ["MASTER_ADDR"] == "master_addr"
        assert environ["MASTER_PORT"] == "2343"
        assert environ["RANK"] == "1"
        assert environ["WORLD_SIZE"] == "10"

        dist.init_process_group.assert_called()
        dist.destroy_process_group.assert_called()

        pytorch_func.assert_called_once_with("a", "b", foo="bar")