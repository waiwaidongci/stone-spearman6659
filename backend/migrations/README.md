Schema is defined by the SQLAlchemy models and created at startup via Base.metadata.create_all. For this local small application no destructive migration is run. Back up named db-data before modifying schemas.

- v1: users / studies / observations / runs / reviews / audits.
- v2: adds match_runs / match_pairs（孔隙率配对）。match_pairs 以 (run_id,pair_index)、(run_id,test_key)、(run_id,control_key) 唯一键保证清单幂等：中断恢复重算同一份配对，INSERT IGNORE 重试不新增，数量写齐才把 match_runs 置为 completed。
