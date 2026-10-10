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

local cycle_num_req = math.floor(now / window)

local data = redis.call('HMGET', key, 'counter_prev', 'counter_curr', 'cycle')
local counter_prev = tonumber(data[1])
local counter_curr = tonumber(data[2])
local cycle_num_curr = tonumber(data[3])

if counter_prev == nil or counter_curr == nil or cycle_num_curr == nil then
    counter_prev = 0
    counter_curr = 0
-- Hereafter, we check which window the current request belongs to
-- If the very next window, rotate counters
elseif cycle_num_req == cycle_num_curr + 1 then
    counter_prev = counter_curr
    counter_curr = 0
-- If beyond the upcoming window, zero counters
elseif cycle_num_req > cycle_num_curr + 1 then
    counter_prev = 0
    counter_curr = 0
end
-- cycle_num_req == cycle_num_curr: (current active window) keep stored counters

cycle_num_curr = cycle_num_req

local tc = now - (cycle_num_curr * window)
local tp = window - tc
local estimate = (tp / window) * counter_prev + counter_curr

if estimate >= limit then
    -- If rotated, save updated counters even on deny; don't refresh TTL.
    redis.call('HSET', key, 'counter_prev', counter_prev, 'counter_curr', counter_curr, 'cycle', cycle_num_curr)
    return {0, math.floor(estimate)}
end

counter_curr = counter_curr + 1
estimate = (tp / window) * counter_prev + counter_curr

redis.call('HSET', key, 'counter_prev', counter_prev, 'counter_curr', counter_curr, 'cycle', cycle_num_curr)
-- Expire at end_of_current + 2*W == (cycle_num_curr + 3) * W
redis.call('PEXPIREAT', key, (cycle_num_curr + 3) * window)

return {1, math.floor(estimate)}
