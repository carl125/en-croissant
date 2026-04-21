GET /v1/puzzles/daily/2021-01-01 HTTP/2
Host: api.chess.com
Accept: */*
X-Client-Version: iOS4.9.48
X-Chesscom-Ps-Id: <ps-id>
X-Chesscom-Device-Id: <device-id>
Accept-Language: en-GB,en-US;q=0.9,en;q=0.8
User-Agent: Chesscom-iOS/4.9.48.24199 (iPhone; iOS 17.5; #ios_developers on Slack)
X-Chesscom-Bucketing-Id: <device-id>
Accept-Encoding: gzip, deflate, br

HTTP/2 200 OK
Date: Mon, 20 Apr 2026 15:14:10 GMT
Content-Type: application/json
Cache-Control: max-age=2, public
Vary: Accept-Encoding
Vary: Accept-Language
Content-Language: en,en
Allow: GET
X-Chesscom-Version: 20260420144615
X-Chesscom-Matched: chess_api_dailypuzzle_getpuzzlebydate
X-Chesscom-Request-Id-Lb: ca28def0204af46682ef8619dbd0606f
X-Chesscom-Request-Id-Cdn: 9ef518df9ea95dec-IAD
Nel: {"report_to":"cf-nel","success_fraction":1.0,"max_age":604800}
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Chesscom-Server-Pool: k8s-prod-fpm-puzzles
Cf-Cache-Status: MISS
Set-Cookie: __cf_bm=<cookie>; HttpOnly; Secure; Path=/; Domain=chess.com; Expires=<expires>
Report-To: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=lgqEeGMhkLZivucrr50MmctxMOy1RFMIdMcKB6AbYuPLLYDEOK7Ap1OO3gfdWwTdqag34SSjHx%2BVQa1XV7OMZjMCG1LmLKwGSjZFiGKmSIPKB1li93Uth27trKxDK5wUyQdL2kiHDAVUc%2F%2B5sBuiz5bFxIaZZ92AdY8B%2BNobDkNXOrvZ0L%2FqGTUFXeIiNXw%3D"}]}
Etag: W/"915c6c63b1a7db0cf3b100f12a21412e"
Server: cloudflare
Cf-Ray: 9ef518df9ea95dec-HKG
Alt-Svc: h3=":443"; ma=86400

{"status":"success","data":{"id":9822,"title":"A New Beginning","pgn":"[Result \"*\"]\r\n[FEN \"8/8/5K2/7k/2Bp4/r1p5/Pn6/5R2 w - - 0 1\"]\r\n\r\n1.Be6 Kh4 2.Rf3 c2 3.Rxa3 d3 4.Rc3 *","puzzle_date":1609488000,"comment":null,"forum_topic":{"id":56157102,"subject":"1/1/2021 - A New Beginning","url":"daily-puzzles/1-1-2021-a-new-beginning","post_count":454,"is_locked":false},"video":null,"solved_count":3370,"solved":false,"current_streak":null}}
