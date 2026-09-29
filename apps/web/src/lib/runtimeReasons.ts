/**
 * C6: 前端运行状态纯逻辑（无 DOM / 无网络，可离线测试）
 * - reasonLabel: C1 全部 reason_codes 的中文文案；未知码返回原码（fail-closed）。
 * - normalizeReadiness: 将 /v1/readyz 任意形状响应规范化为 GenerationRuntimeState；
 *   缺字段/字段非法一律 null（未知），绝不误绿。
 */
import type { GenerationRuntimeState } from '../types/job';

const LABEL_MAP: Record<string, string> = {
  NOT_CONFIGURED: '系统未完成初始配置',
  DATABASE_UNAVAILABLE: '数据库连接异常',
  BROKER_UNAVAILABLE: '消息队列不可用',
  WORKER_UNAVAILABLE: '生成 Worker 未就绪',
  DISPATCHER_UNAVAILABLE: '任务调度器未就绪',
  AUTHOR_UNAVAILABLE: '命题服务未就绪',
  SOLVER_UNAVAILABLE: '盲解服务未就绪',
  BUDGET_UNAVAILABLE: '预算服务不可用',
  BUDGET_INSUFFICIENT: '剩余预算不足以受理该计划',
  MODEL_MISMATCH: '模型版本不匹配',
  ISOLATION_MISCONFIG: '隔离环境配置异常',
  HEARTBEAT_STALE: '组件心跳过期',
};

/**
 * 返回 reason_code 的中文文案。
 * 已知码返回固定翻译，未知码原样返回（fail-closed）。
 */
export function reasonLabel(code: string): string {
  return LABEL_MAP[code] ?? code;
}

/** 将未知值安全转为 boolean | null。undefined/null/非bool → null（未知）。 */
function boolOrNull(val: unknown): boolean | null {
  return typeof val === 'boolean' ? val : null;
}

/**
 * 将服务端任意形状的 /v1/readyz 响应规范化为 GenerationRuntimeState。
 * 契约字段位于 generation 下（C1），同时兼容顶层扁平形状。
 * fail-closed：缺字段/字段非法 → null；ready 仅在服务端 ready===true
 * 且所有组件 ok===true 时为 true；configured 单独为 true 不能撑绿。
 */
export function normalizeReadiness(body: Record<string, unknown>): GenerationRuntimeState {
  const generation = body && typeof body === 'object' && body.generation && typeof body.generation === 'object'
    ? body.generation as Record<string, unknown>
    : body;

  const configured = boolOrNull(generation.configured);
  const serverReady = boolOrNull(generation.ready);
  const reasonCodes: string[] = Array.isArray(generation.reason_codes)
    ? generation.reason_codes.filter((c): c is string => typeof c === 'string')
    : [];
  const checkedAt = typeof generation.checked_at === 'string' ? generation.checked_at : null;

  const components: Record<string, { ok: boolean | null }> = {};
  const rawComponents = generation.components;
  if (rawComponents && typeof rawComponents === 'object' && !Array.isArray(rawComponents)) {
    for (const [key, val] of Object.entries(rawComponents as Record<string, unknown>)) {
      components[key] = val && typeof val === 'object'
        ? { ok: boolOrNull((val as Record<string, unknown>).ok) }
        : { ok: null };
    }
  }

  // ready 判定与 configured 解耦：configured 单独为 true 不能撑绿。
  let ready: boolean | null;
  if (serverReady !== true) {
    ready = serverReady === false ? false : null;
  } else {
    const keys = Object.keys(components);
    if (keys.length === 0) {
      ready = null; // 无组件信息则无法确认就绪
    } else if (keys.every(k => components[k].ok === true)) {
      ready = true;
    } else if (keys.some(k => components[k].ok === false)) {
      ready = false;
    } else {
      ready = null; // 存在组件状态未知，fail-closed
    }
  }

  // 仅当服务端返回新契约必含字段（ready 布尔或 checked_at）时才视为版本已确认；
  // 旧服务仅返回 configured 时 versionConfirmed=false，前端显示"服务状态未确认"，绝不误绿。
  const versionConfirmed =
    typeof generation.ready === 'boolean'
    || typeof generation.checked_at === 'string';

  return { ready, configured, reasonCodes, components, checkedAt, versionConfirmed };
}
