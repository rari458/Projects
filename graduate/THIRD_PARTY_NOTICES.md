# Third-party notices

This package includes source derived from the projects below. Both are MIT-licensed, and
their copyright notices are reproduced here as that licence requires. The full permission
and warranty text is identical to the one in [`LICENSE`](LICENSE).

## Muon — `muonsam/muon.py`

https://github.com/KellerJordan/Muon

```
Copyright (c) 2024 Keller Jordan
```

Adapted with two deliberate modifications, documented in the file's own header: parameters
without gradients take a zero-gradient update rather than being skipped, and Newton-Schulz
runs in fp32 on CPU (the CUDA bf16 path is byte-identical to upstream).

## SAM — `muonsam/sam.py`

https://github.com/davda54/sam

```
Copyright (c) 2021 David Samuel
```

Included unmodified in substance as the generalization baseline this project compares
against. It is not part of the contribution.
