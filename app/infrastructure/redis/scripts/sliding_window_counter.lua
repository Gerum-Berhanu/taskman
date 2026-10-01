-- Sliding-window counter (approximate).
-- KEYS[1] = rate-limit key
-- ARGV[1] = now (unix time; same unit as window)
-- ARGV[2] = window W (cycle length)
-- ARGV[3] = limit
-- Returns {allowed (0|1), estimated_count}

local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

local cycle_req = math.floor(now / window)

local data = redis.call('HMGET', key, 'cp', 'cc', 'cycle')
local cp = tonumber(data[1])
local cc = tonumber(data[2])
local cycle_num = tonumber(data[3])

if cp == nil or cc == nil or cycle_num == nil then
    cp = 0
    cc = 0
-- Hereafter, we check which window the current request belongs to
-- If the very next window, rotate counters
elseif cycle_req == cycle_num + 1 then
    cp = cc
    cc = 0
-- If beyond the upcoming window, zero counters
elseif cycle_req > cycle_num + 1 then
    cp = 0
    cc = 0
end
-- cycle_req == cycle_num: (current active window) keep stored counters

cycle_num = cycle_req

local tc = now - (cycle_num * window)
local tp = window - tc
local estimate = (tp / window) * cp + cc

if estimate >= limit then
    -- If rotated, save updated counters even on deny; don't refresh TTL.
    redis.call('HSET', key, 'cp', cp, 'cc', cc, 'cycle', cycle_num)
    return {0, math.floor(estimate)}
end

cc = cc + 1
estimate = (tp / window) * cp + cc

redis.call('HSET', key, 'cp', cp, 'cc', cc, 'cycle', cycle_num)
-- Expire at end_of_current + 2*W == (cycle_num + 3) * W
redis.call('PEXPIREAT', key, (cycle_num + 3) * window)

return {1, math.floor(estimate)}
