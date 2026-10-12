-- Exact ZSET sliding-window log.
-- Returns {allowed (0|1), retry_after_ms}; 0 when allowed.
-- On deny: ms until the oldest entry leaves the window.

local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_score = tonumber(oldest[2])
    local retry_after_ms = math.ceil(oldest_score + window - now)
    if retry_after_ms < 1 then
        retry_after_ms = 1
    end
    return {0, retry_after_ms}
end

redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window)
return {1, 0}
