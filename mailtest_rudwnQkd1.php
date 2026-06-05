<?php
$result = mail(
    'across1211@naver.com',
    '=?UTF-8?B?' . base64_encode('메일 테스트') . '?=',
    '패스트 코멧 mail() 테스트입니다.',
    implode("\r\n", [
        'From: admin@newscommu.com',
        'Content-Type: text/plain; charset=UTF-8',
    ]),
    '-f admin@newscommu.com'
);
echo $result ? '✅ mail() 호출 성공 (메일 확인하세요)' : '❌ mail() 호출 실패';
