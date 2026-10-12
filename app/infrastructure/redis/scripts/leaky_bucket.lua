local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

-- In the web API leaky bucket implementation, we choose to focus on a single request/token.
-- Why? Because the web API leaky bucket is functionally the exact same thing as token bucket.
-- So, let's make it different by making it stricter for burst activities (allow only 1 request per period)
-- For example, for 30 requests per 60 seconds limit, we scale it down to the one request
--      we want to individually manage. That is 1 request per 2 seconds.
-- That means, there has to be at least a 2 seconds gap between the processing of consecutive requests.

-- Thus:
-- The strict leaky bucket algorithm smooths out request throughput by enforcing a uniform time gap
--      between consecutive requests with zero burst tolerance.
-- Returns {allowed (0|1), retry_after_ms}; 0 when allowed.

-- Key: last_leaked
-- Nutshell: if `now - last_leaked < window / limit`, deny. Else, accept and update last_leaked to `now`.

-- Procedure:
-- Get last_leaked. Don't init if missing; continue with `nil`.
-- Calculate gap = window / limit. E.g. 2 seconds gap per 1 request accepted.
-- If last_leaked is not nil and `now - last_leaked < gap`, deny with remaining gap.
-- Else, accept and update last_leaked to `now`.
-- Set/update expiry to gap.

local last_leaked = tonumber(redis.call("GET", key))
local gap = window / limit

if last_leaked ~= nil and now - last_leaked < gap then
    local remaining = gap - (now - last_leaked)
    return {0, math.ceil(remaining)}
end

redis.call("SET", key, now)
redis.call("PEXPIRE", key, math.ceil(gap)) -- ceil so fractional gaps don't get floored (0.5 -> 0)
return {1, 0}
