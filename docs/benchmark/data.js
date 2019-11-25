window.BENCHMARK_DATA = {
  "lastUpdate": 1574693103957,
  "repoUrl": "https://github.com/Leosocy/cacheorm",
  "entries": {
    "Python Benchmark with pytest-benchmark": [
      {
        "commit": {
          "author": {
            "email": "leosocy@gmail.com",
            "name": "leosocy",
            "username": "Leosocy"
          },
          "committer": {
            "email": "leosocy@gmail.com",
            "name": "leosocy",
            "username": "Leosocy"
          },
          "distinct": true,
          "id": "559f09efdf61544bb68ba047e3c378e354f5f222",
          "message": "ci(workflow): add cache action",
          "timestamp": "2019-11-25T22:40:49+08:00",
          "tree_id": "ffad1ce7917f23eb8846a43c5dc62babcc3b635c",
          "url": "https://github.com/Leosocy/cacheorm/commit/559f09efdf61544bb68ba047e3c378e354f5f222"
        },
        "date": 1574693103475,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/test_backends.py::test_benchmark_backend_set[simple]",
            "value": 564913.0504803557,
            "unit": "iter/sec",
            "range": "stddev: 8.088423400976354e-8",
            "extra": "mean: 0.0000017701839232598392 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_set[redis]",
            "value": 3930.8301873282876,
            "unit": "iter/sec",
            "range": "stddev: 0.000013004106618637992",
            "extra": "mean: 0.00025439918601003766 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_set[memcached]",
            "value": 5967.8861021362945,
            "unit": "iter/sec",
            "range": "stddev: 0.0000054089820806170716",
            "extra": "mean: 0.00016756351962582443 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_set_many[simple]",
            "value": 228917.9394280959,
            "unit": "iter/sec",
            "range": "stddev: 1.9754412586564794e-7",
            "extra": "mean: 0.000004368377605085443 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_set_many[redis]",
            "value": 2927.2950043060914,
            "unit": "iter/sec",
            "range": "stddev: 0.000014251098308107866",
            "extra": "mean: 0.00034161230710570207 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_set_many[memcached]",
            "value": 3118.463263472019,
            "unit": "iter/sec",
            "range": "stddev: 0.000012517212635186288",
            "extra": "mean: 0.00032067076489675396 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_get[simple]",
            "value": 665774.9884868874,
            "unit": "iter/sec",
            "range": "stddev: 5.7327880713624885e-8",
            "extra": "mean: 0.0000015020089629271122 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_get[redis]",
            "value": 4179.533231431906,
            "unit": "iter/sec",
            "range": "stddev: 0.000007838007457238857",
            "extra": "mean: 0.00023926116736662498 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_get[memcached]",
            "value": 6015.541875440209,
            "unit": "iter/sec",
            "range": "stddev: 0.000007275251267478532",
            "extra": "mean: 0.00016623606330174888 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_get_many[simple]",
            "value": 270168.68149009306,
            "unit": "iter/sec",
            "range": "stddev: 1.3022375907453185e-7",
            "extra": "mean: 0.0000037013912733503466 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_get_many[redis]",
            "value": 3857.3613586716756,
            "unit": "iter/sec",
            "range": "stddev: 0.000013989876471358764",
            "extra": "mean: 0.00025924457343150264 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_get_many[memcached]",
            "value": 5769.959860917122,
            "unit": "iter/sec",
            "range": "stddev: 0.000005049779834302343",
            "extra": "mean: 0.00017331143094660148 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_replace[simple]",
            "value": 626202.7956727165,
            "unit": "iter/sec",
            "range": "stddev: 7.659520853022048e-8",
            "extra": "mean: 0.0000015969267574503902 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_replace[redis]",
            "value": 3839.809615043033,
            "unit": "iter/sec",
            "range": "stddev: 0.000009953741105744892",
            "extra": "mean: 0.00026042957861305136 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_replace[memcached]",
            "value": 5683.740425074826,
            "unit": "iter/sec",
            "range": "stddev: 0.00001768525508912716",
            "extra": "mean: 0.000175940476730486 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_replace_many[simple]",
            "value": 259600.327764272,
            "unit": "iter/sec",
            "range": "stddev: 1.1464362409652539e-7",
            "extra": "mean: 0.000003852075259735581 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_replace_many[redis]",
            "value": 2728.212085862768,
            "unit": "iter/sec",
            "range": "stddev: 0.000019190748922496793",
            "extra": "mean: 0.000366540418606701 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_replace_many[memcached]",
            "value": 2935.039090845409,
            "unit": "iter/sec",
            "range": "stddev: 0.000026844648306584356",
            "extra": "mean: 0.0003407109646747363 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_delete[simple]",
            "value": 2411322.401400621,
            "unit": "iter/sec",
            "range": "stddev: 1.5473012300793403e-8",
            "extra": "mean: 4.147102019286796e-7 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_delete[redis]",
            "value": 4298.2085993139335,
            "unit": "iter/sec",
            "range": "stddev: 0.000010058159031550535",
            "extra": "mean: 0.00023265506475409704 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_delete[memcached]",
            "value": 6397.549588192793,
            "unit": "iter/sec",
            "range": "stddev: 0.000005864241461541326",
            "extra": "mean: 0.00015630984742120372 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_delete_many[simple]",
            "value": 800519.081659351,
            "unit": "iter/sec",
            "range": "stddev: 4.9386667237992337e-8",
            "extra": "mean: 0.0000012491894608272877 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_delete_many[redis]",
            "value": 4198.908256538644,
            "unit": "iter/sec",
            "range": "stddev: 0.000009763096359094875",
            "extra": "mean: 0.0002381571444059953 sec\nrounds: 20"
          },
          {
            "name": "tests/test_backends.py::test_benchmark_backend_delete_many[memcached]",
            "value": 3211.6414333173643,
            "unit": "iter/sec",
            "range": "stddev: 0.00002301753387828993",
            "extra": "mean: 0.00031136726211900977 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_dumps[json]",
            "value": 102158.67408238891,
            "unit": "iter/sec",
            "range": "stddev: 1.7473929923717504e-7",
            "extra": "mean: 0.000009788693999625722 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_dumps[msgpack]",
            "value": 521503.0704632981,
            "unit": "iter/sec",
            "range": "stddev: 7.446209890554103e-8",
            "extra": "mean: 0.0000019175342517381724 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_dumps[pickle]",
            "value": 577217.7902744301,
            "unit": "iter/sec",
            "range": "stddev: 5.969312241804751e-8",
            "extra": "mean: 0.0000017324483355313152 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_dumps[protobuf.user]",
            "value": 119170.52907700813,
            "unit": "iter/sec",
            "range": "stddev: 2.5238121166968594e-7",
            "extra": "mean: 0.000008391336412996865 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_loads[json]",
            "value": 141716.24073294405,
            "unit": "iter/sec",
            "range": "stddev: 2.6709324902591854e-7",
            "extra": "mean: 0.000007056354267006288 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_loads[msgpack]",
            "value": 510277.18644922884,
            "unit": "iter/sec",
            "range": "stddev: 7.331352622440042e-8",
            "extra": "mean: 0.0000019597192007710836 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_loads[pickle]",
            "value": 447637.12460753054,
            "unit": "iter/sec",
            "range": "stddev: 8.245417904270536e-8",
            "extra": "mean: 0.0000022339523355592058 sec\nrounds: 20"
          },
          {
            "name": "tests/test_serializers.py::test_benchmark_serializer_loads[protobuf.user]",
            "value": 20457.031163271764,
            "unit": "iter/sec",
            "range": "stddev: 0.0000015175227335285687",
            "extra": "mean: 0.000048882948460057316 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_insert",
            "value": 1364.359257591292,
            "unit": "iter/sec",
            "range": "stddev: 0.0000283061320477449",
            "extra": "mean: 0.0007329447830078494 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_insert_many",
            "value": 820.2662117626769,
            "unit": "iter/sec",
            "range": "stddev: 0.000047224259190101206",
            "extra": "mean: 0.001219116410818741 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_query",
            "value": 2448.484983645908,
            "unit": "iter/sec",
            "range": "stddev: 0.0000735893010020466",
            "extra": "mean: 0.0004084158190388219 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_query_many",
            "value": 1519.8634052756288,
            "unit": "iter/sec",
            "range": "stddev: 0.00002292943315462386",
            "extra": "mean: 0.0006579538638333417 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_update",
            "value": 1291.896967719401,
            "unit": "iter/sec",
            "range": "stddev: 0.00005065843545559001",
            "extra": "mean: 0.0007740555361510835 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_update_many",
            "value": 740.8524074679975,
            "unit": "iter/sec",
            "range": "stddev: 0.00004338188696799511",
            "extra": "mean: 0.0013497965180644931 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_delete",
            "value": 3509.179539865603,
            "unit": "iter/sec",
            "range": "stddev: 0.00001848891747597989",
            "extra": "mean: 0.00028496689572010296 sec\nrounds: 20"
          },
          {
            "name": "tests/test_models/test_benchmark.py::test_benchmark_delete_many",
            "value": 3341.718697892051,
            "unit": "iter/sec",
            "range": "stddev: 0.000009434275868354295",
            "extra": "mean: 0.0002992472109129946 sec\nrounds: 20"
          }
        ]
      }
    ]
  }
}