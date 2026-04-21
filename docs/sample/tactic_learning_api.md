GET /v1/tactics/learning?maxRating=1725&minRating=100&missed=0&themes%5B%5D=3&themes%5B%5D=8 HTTP/2
Host: api.chess.com
Accept: */*
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjU0OGRmOTcwZGEzYzRjMWFkNjAwYTk3NTg3YzIxM2E0MTkwYjNjZWYifQ.eyJhdWQiOiIxZjkzNDkyNC00OTYxLTExZWQtOTM5ZC00MWY5ODZkZmIzZDMiLCJqdGkiOiI5ZWI5MmMxOTQyNmQ2NjA5NmVkMmQ2MDA0YWZkN2VlMWMxZGI5NTkxNmM5OWRkMzBhZjgwYTkzMzM4ZTU1NWQ4ZmUyZjRhY2NkYTE1YmM1OSIsImlhdCI6MTc3NjY4NTM2Ni43MTQxMSwibmJmIjoxNzc2Njg1MzY2LjcxNDExMywiZXhwIjoxNzc2NzcxNzY2LjcwNDkyLCJzdWIiOiJhNDZiYWI5YS0wYjU2LTExZjEtOTU1NS00MTk1NGQyZGJiYzEiLCJzY29wZXMiOltdLCJsb2NhbGUiOiJlbl9VUyJ9.Tq-2F6rM5der3CWvyuA1H7Yq9Imw4ZkCCAnUukZ60yWX6vBEmp0rg2XW0B5qIQDtYGu8kKbkM_Y5HUpJPk_ZXDntZWBrtzIkWURivK5S0ljhf2_ziNvG2WWXzUwQCwy2pEg5WToaaRK9-qNfHljGY32Ueqacm77YlRCTUOMZ1lj5PB7d3rFrIGTdELu7Vx_2pLBrvgaDV2pd_HLARr6AfcJiFoPzTToUqou4fSSakXZIWp3brfUm9Mc_Z_minIIHAr5cVZVlCjLpUz7MjZnvmRCaP-L2fM_tFqPOwV52AuiBZhlqiJ44q4ZYc395lSTBd8EwnqrgrMwk79Qakn-pxQ
X-Client-Version: iOS4.9.48
X-Chesscom-Bucketing-Id: F128727CAA2744C785572B308F24CD47
Accept-Encoding: gzip, deflate, br
If-None-Match: W/"fc9a85d0559ac4324ae2037618d0fe6d"
Accept-Language: en-VN;q=1, vi-VN;q=0.9
User-Agent: Chesscom-iOS/4.9.48.24199 (iPhone; iOS 17.5; #ios_developers on Slack)
X-Chesscom-Device-Id: F128727CAA2744C785572B308F24CD47
X-Chesscom-Ps-Id: 8047EBC4-FC40-4485-9E80-D37E677E228E

HTTP/2 200 OK
Date: Tue, 21 Apr 2026 05:39:54 GMT
Content-Type: application/json
Cache-Control: max-age=2, public
Vary: Accept-Encoding
Vary: Accept-Language
Content-Language: en
Allow: GET, POST
X-Chesscom-Version: 20260420203429
X-Chesscom-Matched: chess_api_tactics_getlearningtactics
X-Chesscom-Meta: username=tuna2343
Nel: {"report_to":"cf-nel","success_fraction":1.0,"max_age":604800}
X-Chesscom-Request-Id-Lb: d7c45e2e6a7a41a588816fcf90a9057f
X-Chesscom-Request-Id-Cdn: 9efa0d09391dabcb-IAD
Report-To: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=Kjy8YHsd3jMhE0aJuYdqXAjMoyl8S7bV%2BAXtof7qepR1y4oKsGsYv31q31nJxlKYWKqlkTmlO8SoWCFMt05qRw69ziI5q5Tz6WyiSqPjGW6VG7xq8Wo2cmojuuBq%2FDss517GYrbfAtMqzTK4K5h6HEMQe92gHCAC9W1HiRKilv8Llgtt%2FvpZr4U3i%2Fd0zhQ%3D"}]}
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Chesscom-Server-Pool: k8s-prod-fpm-puzzles
Cf-Cache-Status: EXPIRED
Set-Cookie: __cf_bm=CJsf2tNXzFCw2eDXI6YXBLI2Ho.lxOTPDeTmJJovWIc-1776749994.4397295-1.0.1.1-4_Oou35bPmBH0IiJE6AG3eEM7aovH_vcL6TV.ED9R6oCtDJ8eYuMDKN.cgDskIPlGnMthQbZDf2KjBL6ejCpChXwDff_GvQ7B4pCRmz3V09FX9f5MGQlOHgQzr6Yp7jVm3.bksv18vVK7kC.KdVYMg; HttpOnly; Secure; Path=/; Domain=chess.com; Expires=Tue, 21 Apr 2026 06:09:54 GMT
Etag: W/"bf9138d8e723eb079a548b9c8616ba12"
Server: cloudflare
Cf-Ray: 9efa0d09391dabcb-HKG
Alt-Svc: h3=":443"; ma=86400

{"status":"success","data":{"is_rating_provisional":false,"id":616542,"initial_fen":"2kr1b1N/ppp1q1pp/5n2/8/2N5/5p2/PP3PPP/R1B1R1K1 w - - 0 1","clean_move_string":"1. Rxe7 Rd1+ 2. Re1 Rxe1# ","attempt_count":15628,"passed_count":9745,"rating":913,"average_seconds":13,"user_moves_first":false,"themes":[{"id":3,"name":"Back Rank"},{"id":15,"name":"Mate in 2"},{"id":50,"name":"Rooks on Seventh"}],"user_position":2,"move_count":2}}