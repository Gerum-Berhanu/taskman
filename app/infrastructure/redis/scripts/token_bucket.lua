local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

-- Key stores two values: the counter (available tokens) and the last_req_at (last request at)
-- Returns {allowed (0|1), retry_after_ms}; 0 when allowed.

-- Procedure:
-- Get key values (counter and last_req_at); if missing/invalid, init with limit and now, expire at window
-- Calculate time delta: delta = now - last_req_at
-- Calculate new tokens generated since last request: new_tokens = (limit / window) * delta
-- Calculate total tokens: total_tokens = counter + new_tokens
-- Cap the total available tokens at limit by taking the available_tokens = min(limit, total_tokens)
-- If available_tokens < 1, deny with time to refill one token. Else, allow, deduct 1, update key

local counter = tonumber(redis.call("HGET", key, "counter"))
local last_req_at = tonumber(redis.call("HGET", key, "last_req_at"))

if counter == nil or last_req_at == nil then
    redis.call("HSET", key, "counter", limit, "last_req_at", now)
    redis.call("PEXPIRE", key, window)
    counter = limit
    last_req_at = now
end

local delta = now - last_req_at
local new_tokens = (limit / window) * delta
local total_tokens = counter + new_tokens
local available_tokens = math.min(limit, total_tokens)

if available_tokens < 1 then
    -- ms until one full token is available at rate limit/window
    local retry_after_ms = math.ceil((1 - available_tokens) * window / limit)
    return {0, retry_after_ms}
end

available_tokens = available_tokens - 1
redis.call("HSET", key, "counter", available_tokens, "last_req_at", now)
redis.call("PEXPIRE", key, window)
return {1, 0}
