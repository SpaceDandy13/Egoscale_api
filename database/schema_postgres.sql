-- 警告表
CREATE TABLE IF NOT EXISTS warns (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  server_id VARCHAR(20) NOT NULL,
  moderator_id VARCHAR(20) NOT NULL,
  reason VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 用户积分表
CREATE TABLE IF NOT EXISTS user_points (
  user_id VARCHAR(20) NOT NULL,
  server_id VARCHAR(20) NOT NULL,
  points INTEGER NOT NULL DEFAULT 0,
  total_checkins INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, server_id)
);

-- 签到记录表
CREATE TABLE IF NOT EXISTS daily_checkins (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  server_id VARCHAR(20) NOT NULL,
  checkin_date DATE NOT NULL,
  points_earned INTEGER NOT NULL DEFAULT 10,
  streak_count INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, server_id, checkin_date)
);

-- 消息记录表（用于滑动窗口计算）
CREATE TABLE IF NOT EXISTS message_logs (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  server_id VARCHAR(20) NOT NULL,
  message_time TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 每日活跃奖励记录表
CREATE TABLE IF NOT EXISTS daily_activity_rewards (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  server_id VARCHAR(20) NOT NULL,
  reward_date DATE NOT NULL,
  points_earned INTEGER NOT NULL DEFAULT 0,
  message_count_when_rewarded INTEGER NOT NULL,
  reward_time TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, server_id, reward_date)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_warns_user_server ON warns(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_user_points_server ON user_points(server_id);
CREATE INDEX IF NOT EXISTS idx_checkins_user_server ON daily_checkins(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_checkins_date ON daily_checkins(checkin_date);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_message_logs_user_server ON message_logs(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_message_logs_time ON message_logs(message_time);
CREATE INDEX IF NOT EXISTS idx_daily_activity_rewards_user_server ON daily_activity_rewards(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_daily_activity_rewards_date ON daily_activity_rewards(reward_date);


-- Twitter验证记录表
CREATE TABLE IF NOT EXISTS twitter_verifications (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  server_id VARCHAR(20) NOT NULL,
  twitter_username VARCHAR(50) NOT NULL,
  tweet_id VARCHAR(30) NOT NULL,
  action_type VARCHAR(20) NOT NULL, -- 'like', 'retweet', 'reply'
  points_earned INTEGER NOT NULL DEFAULT 0,
  verified_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, server_id, tweet_id, action_type)
);

-- Twitter用户绑定表
CREATE TABLE IF NOT EXISTS twitter_bindings (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  server_id VARCHAR(20) NOT NULL,
  twitter_username VARCHAR(50) NOT NULL,
  twitter_user_id VARCHAR(30) NOT NULL,
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMP,
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, server_id)
);

-- Twitter目标推文表
CREATE TABLE IF NOT EXISTS twitter_target_tweets (
  id SERIAL PRIMARY KEY,
  server_id VARCHAR(20) NOT NULL,
  tweet_id VARCHAR(30) NOT NULL,
  tweet_url VARCHAR(500) NOT NULL,
  description VARCHAR(255) DEFAULT NULL,
  like_points INTEGER NOT NULL DEFAULT 5,
  retweet_points INTEGER NOT NULL DEFAULT 10,
  reply_points INTEGER NOT NULL DEFAULT 15,
  triple_bonus_points INTEGER NOT NULL DEFAULT 20,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(server_id, tweet_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_twitter_verifications_user_server ON twitter_verifications(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_twitter_verifications_tweet ON twitter_verifications(tweet_id);
CREATE INDEX IF NOT EXISTS idx_twitter_bindings_user_server ON twitter_bindings(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_twitter_target_tweets_server ON twitter_target_tweets(server_id);


-- 服务器配置表
CREATE TABLE IF NOT EXISTS server_config (
  id SERIAL PRIMARY KEY,
  server_id VARCHAR(20) NOT NULL,
  config_key VARCHAR(50) NOT NULL,
  config_value VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(server_id, config_key)
);

CREATE INDEX IF NOT EXISTS idx_server_config_server ON server_config(server_id);


-- OAuth临时存储表
CREATE TABLE IF NOT EXISTS oauth_temp_storage (
  id SERIAL PRIMARY KEY,
  state VARCHAR(100) NOT NULL UNIQUE,
  code_verifier VARCHAR(128) NOT NULL,
  discord_user_id VARCHAR(20) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL DEFAULT (NOW() + INTERVAL '10 minutes')
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_oauth_temp_storage_state ON oauth_temp_storage(state);
CREATE INDEX IF NOT EXISTS idx_oauth_temp_storage_expires ON oauth_temp_storage(expires_at);


-- 管理员操作审计日志表
CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL, -- 'add_points', 'remove_points'
    operator_user_id VARCHAR(20) NOT NULL, -- 执行操作的管理员
    operator_username VARCHAR(100) NOT NULL, -- 管理员用户名
    target_user_id VARCHAR(20) NOT NULL,  -- 被操作的用户
    target_username VARCHAR(100) NOT NULL, -- 被操作用户名
    server_id VARCHAR(20) NOT NULL,
    
    -- 操作详情
    points_change INTEGER NOT NULL,       -- 积分变化量（正数为增加，负数为扣除）
    points_before INTEGER NOT NULL,       -- 操作前积分
    points_after INTEGER NOT NULL,        -- 操作后积分
    reason VARCHAR(500) NOT NULL,         -- 操作原因（必填）
    
    -- 元数据
    operation_time TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_operator ON admin_audit_logs(operator_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target ON admin_audit_logs(target_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_server ON admin_audit_logs(server_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON admin_audit_logs(operation_time);
CREATE INDEX IF NOT EXISTS idx_audit_logs_type ON admin_audit_logs(operation_type);


-- Early role 用户信息登记表
CREATE TABLE IF NOT EXISTS early_role_members (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  guild_id VARCHAR(20) NOT NULL,
  wallet_address VARCHAR(128) DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (guild_id, user_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_early_role_members_guild_user ON early_role_members (guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_early_role_members_wallet ON early_role_members (wallet_address);