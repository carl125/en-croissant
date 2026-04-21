POST /v1/tactics/challenge/tactics HTTP/2
Host: api.chess.com
Content-Type: application/x-www-form-urlencoded
Accept: */*
Authorization: Bearer <token>
X-Client-Version: iOS4.9.48
X-Chesscom-Bucketing-Id: <device-id>
Accept-Encoding: gzip, deflate, br
Accept-Language: en-VN;q=1, vi-VN;q=0.9
Content-Length: 69
User-Agent: Chesscom-iOS/4.9.48.24199 (iPhone; iOS 17.5; #ios_developers on Slack)
X-Chesscom-Device-Id: <device-id>
X-Chesscom-Ps-Id: <ps-id>

batchSize=2&challengeId=7af5f22c-3caf-11f1-ae80-79e33a852428&step=17

HTTP/2 200 OK
Date: Mon, 20 Apr 2026 12:33:44 GMT
Content-Type: application/json
Report-To: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=rYM3Iv6ABXznlV4oigivCVT%2BY9C6aos9YUPdw1IKFPwsiKEPVUkfYp61tgclsUfAWpuI2NzxU7xqj4CsHewiqnjpVTEpYp%2B5iOGsLDqBH%2FP%2BB2WSqiCSYWfm6Yg8JRzLML1O75qGfrhNPvjUATUq3s5enwTxApkvmCGY2%2BiWk53fx7Q21zKYxBg6Z7yJwL0%3D"}]}
Cache-Control: no-cache, private
Vary: accept-encoding, accept-language
Content-Language: en
Allow: POST
X-Chesscom-Version: 20260420105021
X-Chesscom-Matched: chess_api_tacticschallenge_posttactics
X-Chesscom-Meta: username=tuna2343
Nel: {"report_to":"cf-nel","success_fraction":1.0,"max_age":604800}
X-Chesscom-Request-Id-Lb: ecb5cd7e44d5650458d36e2a495f9153
X-Chesscom-Request-Id-Cdn: 9ef42dd9f885c3e8-IAD
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Chesscom-Server-Pool: k8s-prod-fpm-puzzles
Cf-Cache-Status: DYNAMIC
Set-Cookie: __cf_bm=<cookie>; HttpOnly; Secure; Path=/; Domain=chess.com; Expires=<expires>
Server: cloudflare
Cf-Ray: 9ef42dd9f885c3e8-HKG
Alt-Svc: h3=":443"; ma=86400

{"status":"success","data":{"tactics":[{"is_rating_provisional":false,"id":2406418,"initial_fen":"r2qkbnr/pp3pp1/2np3p/2p1N3/2B1P1b1/2NP4/PPP2P1P/R1BQK2R b KQkq - 0 7","clean_move_string":"1... Bxd1 2. Bxf7+ ","attempt_count":19233,"passed_count":12174,"rating":975,"average_seconds":15,"user_moves_first":false,"themes":[],"user_position":1,"move_count":1},{"is_rating_provisional":false,"id":27745,"initial_fen":"r7/p2nprbk/7p/2p3pP/2qPN3/1R2B3/P1P2PP1/K1Q4R w - - 0 1","clean_move_string":"1. Bxg5 Qxd4+ 2. c3 Qxe4 ","attempt_count":174773,"passed_count":94372,"rating":1048,"average_seconds":33,"user_moves_first":false,"themes":[{"id":11,"name":"Fork / Double Attack"},{"id":12,"name":"Hanging Piece"}],"user_position":2,"move_count":2}]}}
