local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

-- Key stores two values: the counter and the cycle number (from UNIX epoch / window).
-- TTL: PEXPIREAT at the start of the next cycle ((cycle_req + 1) * window).
-- Returns {allowed (0|1), retry_after_ms}; 0 when allowed.

-- Procedure:
-- Get key values (counter and cycle_key); if missing/invalid, treat as reset
-- Check if the request's window cycle cycle_req (math.floor(now / window)) is NOT equal to cycle_key:
    -- If so, reset key values to 0 and cycle_req, expire at next cycle start
    -- Else, continue
-- Check if counter >= limit
    -- If so, deny: return {0, next_window_start - now}
    -- Else, allow, counter += 1, refresh TTL: return {1, 0}

local cycle_req = math.floor(now / window)

local counter = tonumber(redis.call("HGET", key, "counter"))
local cycle_key = tonumber(redis.call("HGET", key, "cycle_key"))

local next_window_start = (cycle_req + 1) * window

if counter == nil or cycle_key == nil or cycle_req ~= cycle_key then
    -- if the key doesn't exist (or is invalid), reset: counter or cycle_key is nil
    -- if current request is in a new cycle, reset: cycle_req ~= cycle_key
    redis.call("HSET", key, "counter", 0, "cycle_key", cycle_req)
    redis.call("PEXPIREAT", key, next_window_start)
    counter = 0
    cycle_key = cycle_req
end

if counter >= limit then
    return {0, math.ceil(next_window_start - now)}
end

redis.call("HINCRBY", key, "counter", 1)
redis.call("PEXPIREAT", key, next_window_start)
return {1, 0}
