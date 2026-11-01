| Mode | v40-L | v40-M | v40-Q | v40-H |
|---|---:|---:|---:|---:|
| byte | 2953 | 2331 | 1663 | 1273 |
| alphanumeric | 4296 | 3391 | 2420 | 1852 |
| numeric | 7089 | 5596 | 3993 | 3057 |

| Algorithm | PK bytes | Sig bytes | PK base64 | PK base32 | Sig base64 | Sig base32 |
|---|---:|---:|---:|---:|---:|---:|
| ML-DSA-44 | 1312 | 2420 | 1752 | 2100 | 3228 | 3872 |
| ML-DSA-65 | 1952 | 3309 | 2604 | 3124 | 4412 | 5295 |
| ML-DSA-87 | 2592 | 4627 | 3456 | 4148 | 6172 | 7404 |
| SLH-DSA-SHAKE-128s | 32 | 7856 | 44 | 52 | 10476 | 12570 |
| SLH-DSA-SHAKE-192s | 48 | 16224 | 64 | 77 | 21632 | 25959 |
| SLH-DSA-SHAKE-256s | 64 | 29792 | 88 | 103 | 39724 | 47668 |
| SLH-DSA-SHAKE-128f | 32 | 17088 | 44 | 52 | 22784 | 27341 |
| SLH-DSA-SHAKE-256f | 64 | 49856 | 88 | 103 | 66476 | 79770 |

| Algorithm | PK + signature | v40-L bytes | Exact shortfall bytes |
|---|---:|---:|---:|
| ML-DSA-44 | 1312 + 2420 = 3732 | 2953 | 779 |
| ML-DSA-65 | 1952 + 3309 = 5261 | 2953 | 2308 |
| ML-DSA-87 | 2592 + 4627 = 7219 | 2953 | 4266 |
| SLH-DSA-SHAKE-128s | 32 + 7856 = 7888 | 2953 | 4935 |
| SLH-DSA-SHAKE-192s | 48 + 16224 = 16272 | 2953 | 13319 |
| SLH-DSA-SHAKE-256s | 64 + 29792 = 29856 | 2953 | 26903 |
| SLH-DSA-SHAKE-128f | 32 + 17088 = 17120 | 2953 | 14167 |
| SLH-DSA-SHAKE-256f | 64 + 49856 = 49920 | 2953 | 46967 |

| Payload | Mode | EC | Raw bytes | Payload bytes | Encoded characters | Version | Modules/side | Verdict | Shortfall bytes | PNG decode |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| recovery-24-words | byte | L | 187 | 187 | 187 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| recovery-24-words | byte | M | 187 | 187 | 187 | 10 | 57 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| recovery-24-words | byte | Q | 187 | 187 | 187 | 12 | 65 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| recovery-24-words | byte | H | 187 | 187 | 187 | 14 | 73 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | L | 37 | 37 | N/A | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | M | 37 | 37 | N/A | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | Q | 37 | 37 | N/A | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | H | 37 | 37 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | L | 37 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | M | 37 | 52 | 52 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | Q | 37 | 52 | 52 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | H | 37 | 52 | 52 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | L | 37 | 60 | 60 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | M | 37 | 60 | 60 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | Q | 37 | 60 | 60 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | H | 37 | 60 | 60 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| public-single-descriptor-raw | byte | L | 2629 | 2629 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| public-single-descriptor-raw | byte | M | 2629 | 2629 | N/A | N/A | N/A | INFASIBLE | 298 | not encodable |
| public-single-descriptor-raw | byte | Q | 2629 | 2629 | N/A | N/A | N/A | INFASIBLE | 966 | not encodable |
| public-single-descriptor-raw | byte | H | 2629 | 2629 | N/A | N/A | N/A | INFASIBLE | 1356 | not encodable |
| public-single-descriptor-base64 | byte | L | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 555 | not encodable |
| public-single-descriptor-base64 | byte | M | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 1177 | not encodable |
| public-single-descriptor-base64 | byte | Q | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 1845 | not encodable |
| public-single-descriptor-base64 | byte | H | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 2235 | not encodable |
| public-single-descriptor-base32 | alphanumeric | L | 2629 | 4207 | 4207 | 40 | 177 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| public-single-descriptor-base32 | alphanumeric | M | 2629 | 4207 | 4207 | N/A | N/A | INFASIBLE | 816 | not encodable |
| public-single-descriptor-base32 | alphanumeric | Q | 2629 | 4207 | 4207 | N/A | N/A | INFASIBLE | 1787 | not encodable |
| public-single-descriptor-base32 | alphanumeric | H | 2629 | 4207 | 4207 | N/A | N/A | INFASIBLE | 2355 | not encodable |
| public-dual-descriptor-raw | byte | L | 2693 | 2693 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| public-dual-descriptor-raw | byte | M | 2693 | 2693 | N/A | N/A | N/A | INFASIBLE | 362 | not encodable |
| public-dual-descriptor-raw | byte | Q | 2693 | 2693 | N/A | N/A | N/A | INFASIBLE | 1030 | not encodable |
| public-dual-descriptor-raw | byte | H | 2693 | 2693 | N/A | N/A | N/A | INFASIBLE | 1420 | not encodable |
| public-dual-descriptor-base64 | byte | L | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 639 | not encodable |
| public-dual-descriptor-base64 | byte | M | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 1261 | not encodable |
| public-dual-descriptor-base64 | byte | Q | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 1929 | not encodable |
| public-dual-descriptor-base64 | byte | H | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 2319 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | L | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 13 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | M | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 918 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | Q | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 1889 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | H | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 2457 | not encodable |
| root-dual-public-keys-raw | byte | L | 2656 | 2656 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| root-dual-public-keys-raw | byte | M | 2656 | 2656 | N/A | N/A | N/A | INFASIBLE | 325 | not encodable |
| root-dual-public-keys-raw | byte | Q | 2656 | 2656 | N/A | N/A | N/A | INFASIBLE | 993 | not encodable |
| root-dual-public-keys-raw | byte | H | 2656 | 2656 | N/A | N/A | N/A | INFASIBLE | 1383 | not encodable |
| root-dual-public-keys-base64 | byte | L | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 591 | not encodable |
| root-dual-public-keys-base64 | byte | M | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 1213 | not encodable |
| root-dual-public-keys-base64 | byte | Q | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 1881 | not encodable |
| root-dual-public-keys-base64 | byte | H | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 2271 | not encodable |
| root-dual-public-keys-base32 | alphanumeric | L | 2656 | 4250 | 4250 | 40 | 177 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| root-dual-public-keys-base32 | alphanumeric | M | 2656 | 4250 | 4250 | N/A | N/A | INFASIBLE | 859 | not encodable |
| root-dual-public-keys-base32 | alphanumeric | Q | 2656 | 4250 | 4250 | N/A | N/A | INFASIBLE | 1830 | not encodable |
| root-dual-public-keys-base32 | alphanumeric | H | 2656 | 4250 | 4250 | N/A | N/A | INFASIBLE | 2398 | not encodable |
| canonical-birth-raw | byte | L | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 730 | not encodable |
| canonical-birth-raw | byte | M | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 1352 | not encodable |
| canonical-birth-raw | byte | Q | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 2020 | not encodable |
| canonical-birth-raw | byte | H | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 2410 | not encodable |
| canonical-birth-base64 | byte | L | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 1959 | not encodable |
| canonical-birth-base64 | byte | M | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 2581 | not encodable |
| canonical-birth-base64 | byte | Q | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 3249 | not encodable |
| canonical-birth-base64 | byte | H | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 3639 | not encodable |
| canonical-birth-base32 | alphanumeric | L | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 1597 | not encodable |
| canonical-birth-base32 | alphanumeric | M | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 2502 | not encodable |
| canonical-birth-base32 | alphanumeric | Q | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 3473 | not encodable |
| canonical-birth-base32 | alphanumeric | H | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 4041 | not encodable |
| ML-DSA-44-pk-raw | byte | L | 1312 | 1312 | N/A | 26 | 121 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-raw | byte | M | 1312 | 1312 | N/A | 30 | 137 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-raw | byte | Q | 1312 | 1312 | N/A | 36 | 161 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-raw | byte | H | 1312 | 1312 | N/A | N/A | N/A | INFASIBLE | 39 | not encodable |
| ML-DSA-44-pk-base64 | byte | L | 1312 | 1752 | 1752 | 31 | 141 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base64 | byte | M | 1312 | 1752 | 1752 | 35 | 157 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base64 | byte | Q | 1312 | 1752 | 1752 | N/A | N/A | INFASIBLE | 89 | not encodable |
| ML-DSA-44-pk-base64 | byte | H | 1312 | 1752 | 1752 | N/A | N/A | INFASIBLE | 479 | not encodable |
| ML-DSA-44-pk-base32 | alphanumeric | L | 1312 | 2100 | 2100 | 27 | 125 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base32 | alphanumeric | M | 1312 | 2100 | 2100 | 31 | 141 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base32 | alphanumeric | Q | 1312 | 2100 | 2100 | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base32 | alphanumeric | H | 1312 | 2100 | 2100 | N/A | N/A | INFASIBLE | 248 | not encodable |
| ML-DSA-44-signature-raw | byte | L | 2420 | 2420 | N/A | 36 | 161 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-signature-raw | byte | M | 2420 | 2420 | N/A | N/A | N/A | INFASIBLE | 89 | not encodable |
| ML-DSA-44-signature-raw | byte | Q | 2420 | 2420 | N/A | N/A | N/A | INFASIBLE | 757 | not encodable |
| ML-DSA-44-signature-raw | byte | H | 2420 | 2420 | N/A | N/A | N/A | INFASIBLE | 1147 | not encodable |
| ML-DSA-44-signature-base64 | byte | L | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 275 | not encodable |
| ML-DSA-44-signature-base64 | byte | M | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 897 | not encodable |
| ML-DSA-44-signature-base64 | byte | Q | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 1565 | not encodable |
| ML-DSA-44-signature-base64 | byte | H | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 1955 | not encodable |
| ML-DSA-44-signature-base32 | alphanumeric | L | 2420 | 3872 | 3872 | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-signature-base32 | alphanumeric | M | 2420 | 3872 | 3872 | N/A | N/A | INFASIBLE | 481 | not encodable |
| ML-DSA-44-signature-base32 | alphanumeric | Q | 2420 | 3872 | 3872 | N/A | N/A | INFASIBLE | 1452 | not encodable |
| ML-DSA-44-signature-base32 | alphanumeric | H | 2420 | 3872 | 3872 | N/A | N/A | INFASIBLE | 2020 | not encodable |
| ML-DSA-44-pk-signature | byte | L | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 779 | not encodable |
| ML-DSA-44-pk-signature | byte | M | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 1401 | not encodable |
| ML-DSA-44-pk-signature | byte | Q | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 2069 | not encodable |
| ML-DSA-44-pk-signature | byte | H | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 2459 | not encodable |
| ML-DSA-65-pk-raw | byte | L | 1952 | 1952 | N/A | 32 | 145 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-raw | byte | M | 1952 | 1952 | N/A | 37 | 165 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-raw | byte | Q | 1952 | 1952 | N/A | N/A | N/A | INFASIBLE | 289 | not encodable |
| ML-DSA-65-pk-raw | byte | H | 1952 | 1952 | N/A | N/A | N/A | INFASIBLE | 679 | not encodable |
| ML-DSA-65-pk-base64 | byte | L | 1952 | 2604 | 2604 | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-base64 | byte | M | 1952 | 2604 | 2604 | N/A | N/A | INFASIBLE | 273 | not encodable |
| ML-DSA-65-pk-base64 | byte | Q | 1952 | 2604 | 2604 | N/A | N/A | INFASIBLE | 941 | not encodable |
| ML-DSA-65-pk-base64 | byte | H | 1952 | 2604 | 2604 | N/A | N/A | INFASIBLE | 1331 | not encodable |
| ML-DSA-65-pk-base32 | alphanumeric | L | 1952 | 3124 | 3124 | 34 | 153 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-base32 | alphanumeric | M | 1952 | 3124 | 3124 | 39 | 173 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-base32 | alphanumeric | Q | 1952 | 3124 | 3124 | N/A | N/A | INFASIBLE | 704 | not encodable |
| ML-DSA-65-pk-base32 | alphanumeric | H | 1952 | 3124 | 3124 | N/A | N/A | INFASIBLE | 1272 | not encodable |
| ML-DSA-65-signature-raw | byte | L | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 356 | not encodable |
| ML-DSA-65-signature-raw | byte | M | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 978 | not encodable |
| ML-DSA-65-signature-raw | byte | Q | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 1646 | not encodable |
| ML-DSA-65-signature-raw | byte | H | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 2036 | not encodable |
| ML-DSA-65-signature-base64 | byte | L | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 1459 | not encodable |
| ML-DSA-65-signature-base64 | byte | M | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 2081 | not encodable |
| ML-DSA-65-signature-base64 | byte | Q | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 2749 | not encodable |
| ML-DSA-65-signature-base64 | byte | H | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 3139 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | L | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 999 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | M | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 1904 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | Q | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 2875 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | H | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 3443 | not encodable |
| ML-DSA-65-pk-signature | byte | L | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 2308 | not encodable |
| ML-DSA-65-pk-signature | byte | M | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 2930 | not encodable |
| ML-DSA-65-pk-signature | byte | Q | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 3598 | not encodable |
| ML-DSA-65-pk-signature | byte | H | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 3988 | not encodable |
| ML-DSA-87-pk-raw | byte | L | 2592 | 2592 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-87-pk-raw | byte | M | 2592 | 2592 | N/A | N/A | N/A | INFASIBLE | 261 | not encodable |
| ML-DSA-87-pk-raw | byte | Q | 2592 | 2592 | N/A | N/A | N/A | INFASIBLE | 929 | not encodable |
| ML-DSA-87-pk-raw | byte | H | 2592 | 2592 | N/A | N/A | N/A | INFASIBLE | 1319 | not encodable |
| ML-DSA-87-pk-base64 | byte | L | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 503 | not encodable |
| ML-DSA-87-pk-base64 | byte | M | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 1125 | not encodable |
| ML-DSA-87-pk-base64 | byte | Q | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 1793 | not encodable |
| ML-DSA-87-pk-base64 | byte | H | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 2183 | not encodable |
| ML-DSA-87-pk-base32 | alphanumeric | L | 2592 | 4148 | 4148 | 40 | 177 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-87-pk-base32 | alphanumeric | M | 2592 | 4148 | 4148 | N/A | N/A | INFASIBLE | 757 | not encodable |
| ML-DSA-87-pk-base32 | alphanumeric | Q | 2592 | 4148 | 4148 | N/A | N/A | INFASIBLE | 1728 | not encodable |
| ML-DSA-87-pk-base32 | alphanumeric | H | 2592 | 4148 | 4148 | N/A | N/A | INFASIBLE | 2296 | not encodable |
| ML-DSA-87-signature-raw | byte | L | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 1674 | not encodable |
| ML-DSA-87-signature-raw | byte | M | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 2296 | not encodable |
| ML-DSA-87-signature-raw | byte | Q | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 2964 | not encodable |
| ML-DSA-87-signature-raw | byte | H | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 3354 | not encodable |
| ML-DSA-87-signature-base64 | byte | L | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 3219 | not encodable |
| ML-DSA-87-signature-base64 | byte | M | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 3841 | not encodable |
| ML-DSA-87-signature-base64 | byte | Q | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 4509 | not encodable |
| ML-DSA-87-signature-base64 | byte | H | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 4899 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | L | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 3108 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | M | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 4013 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | Q | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 4984 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | H | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 5552 | not encodable |
| ML-DSA-87-pk-signature | byte | L | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 4266 | not encodable |
| ML-DSA-87-pk-signature | byte | M | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 4888 | not encodable |
| ML-DSA-87-pk-signature | byte | Q | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 5556 | not encodable |
| ML-DSA-87-pk-signature | byte | H | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 5946 | not encodable |
| SLH-DSA-SHAKE-128s-pk-raw | byte | L | 32 | 32 | N/A | 2 | 25 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-raw | byte | M | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-raw | byte | Q | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-raw | byte | H | 32 | 32 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | L | 32 | 44 | 44 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | M | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | Q | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | H | 32 | 44 | 44 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | L | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | M | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | Q | 32 | 52 | 52 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | H | 32 | 52 | 52 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-signature-raw | byte | L | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 4903 | not encodable |
| SLH-DSA-SHAKE-128s-signature-raw | byte | M | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 5525 | not encodable |
| SLH-DSA-SHAKE-128s-signature-raw | byte | Q | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 6193 | not encodable |
| SLH-DSA-SHAKE-128s-signature-raw | byte | H | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 6583 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | L | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 7523 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | M | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 8145 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | Q | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 8813 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | H | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 9203 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | L | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 8274 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | M | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 9179 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | Q | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 10150 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | H | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 10718 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | L | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 4935 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | M | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 5557 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | Q | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 6225 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | H | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 6615 | not encodable |
| SLH-DSA-SHAKE-192s-pk-raw | byte | L | 48 | 48 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-raw | byte | M | 48 | 48 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-raw | byte | Q | 48 | 48 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-raw | byte | H | 48 | 48 | N/A | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | L | 48 | 64 | 64 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | M | 48 | 64 | 64 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | Q | 48 | 64 | 64 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | H | 48 | 64 | 64 | 7 | 45 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | L | 48 | 77 | 77 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | M | 48 | 77 | 77 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | Q | 48 | 77 | 77 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | H | 48 | 77 | 77 | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-signature-raw | byte | L | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 13271 | not encodable |
| SLH-DSA-SHAKE-192s-signature-raw | byte | M | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 13893 | not encodable |
| SLH-DSA-SHAKE-192s-signature-raw | byte | Q | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 14561 | not encodable |
| SLH-DSA-SHAKE-192s-signature-raw | byte | H | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 14951 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | L | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 18679 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | M | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 19301 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | Q | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 19969 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | H | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 20359 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | L | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 21663 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | M | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 22568 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | Q | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 23539 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | H | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 24107 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | L | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 13319 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | M | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 13941 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | Q | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 14609 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | H | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 14999 | not encodable |
| SLH-DSA-SHAKE-256s-pk-raw | byte | L | 64 | 64 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-raw | byte | M | 64 | 64 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-raw | byte | Q | 64 | 64 | N/A | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-raw | byte | H | 64 | 64 | N/A | 7 | 45 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | L | 64 | 88 | 88 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | M | 64 | 88 | 88 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | Q | 64 | 88 | 88 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | H | 64 | 88 | 88 | 9 | 53 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | L | 64 | 103 | 103 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | M | 64 | 103 | 103 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | Q | 64 | 103 | 103 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | H | 64 | 103 | 103 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-signature-raw | byte | L | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 26839 | not encodable |
| SLH-DSA-SHAKE-256s-signature-raw | byte | M | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 27461 | not encodable |
| SLH-DSA-SHAKE-256s-signature-raw | byte | Q | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 28129 | not encodable |
| SLH-DSA-SHAKE-256s-signature-raw | byte | H | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 28519 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | L | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 36771 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | M | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 37393 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | Q | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 38061 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | H | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 38451 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | L | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 43372 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | M | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 44277 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | Q | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 45248 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | H | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 45816 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | L | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 26903 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | M | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 27525 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | Q | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 28193 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | H | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 28583 | not encodable |
| SLH-DSA-SHAKE-128f-pk-raw | byte | L | 32 | 32 | N/A | 2 | 25 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-raw | byte | M | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-raw | byte | Q | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-raw | byte | H | 32 | 32 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | L | 32 | 44 | 44 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | M | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | Q | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | H | 32 | 44 | 44 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | L | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | M | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | Q | 32 | 52 | 52 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | H | 32 | 52 | 52 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-signature-raw | byte | L | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 14135 | not encodable |
| SLH-DSA-SHAKE-128f-signature-raw | byte | M | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 14757 | not encodable |
| SLH-DSA-SHAKE-128f-signature-raw | byte | Q | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 15425 | not encodable |
| SLH-DSA-SHAKE-128f-signature-raw | byte | H | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 15815 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | L | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 19831 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | M | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 20453 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | Q | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 21121 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | H | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 21511 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | L | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 23045 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | M | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 23950 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | Q | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 24921 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | H | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 25489 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | L | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 14167 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | M | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 14789 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | Q | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 15457 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | H | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 15847 | not encodable |
| SLH-DSA-SHAKE-256f-pk-raw | byte | L | 64 | 64 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-raw | byte | M | 64 | 64 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-raw | byte | Q | 64 | 64 | N/A | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-raw | byte | H | 64 | 64 | N/A | 7 | 45 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | L | 64 | 88 | 88 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | M | 64 | 88 | 88 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | Q | 64 | 88 | 88 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | H | 64 | 88 | 88 | 9 | 53 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | L | 64 | 103 | 103 | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | M | 64 | 103 | 103 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | Q | 64 | 103 | 103 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | H | 64 | 103 | 103 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-signature-raw | byte | L | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 46903 | not encodable |
| SLH-DSA-SHAKE-256f-signature-raw | byte | M | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 47525 | not encodable |
| SLH-DSA-SHAKE-256f-signature-raw | byte | Q | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 48193 | not encodable |
| SLH-DSA-SHAKE-256f-signature-raw | byte | H | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 48583 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | L | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 63523 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | M | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 64145 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | Q | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 64813 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | H | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 65203 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | L | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 75474 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | M | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 76379 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | Q | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 77350 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | H | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 77918 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | L | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 46967 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | M | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 47589 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | Q | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 48257 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | H | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 48647 | not encodable |
