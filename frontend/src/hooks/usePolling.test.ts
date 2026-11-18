import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POLL_INTERVAL_MS, usePolling } from "./usePolling";

describe("UIG-04, UIG-08: hook usePolling", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("consulta a cada 3 s enquanto a condição está ativa, e não antes", () => {
    const tick = vi.fn();
    renderHook(() => usePolling(tick, true));

    act(() => vi.advanceTimersByTime(POLL_INTERVAL_MS - 1));
    expect(tick).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(tick).toHaveBeenCalledTimes(1);
    act(() => vi.advanceTimersByTime(POLL_INTERVAL_MS));
    expect(tick).toHaveBeenCalledTimes(2);
    expect(POLL_INTERVAL_MS).toBe(3000);
  });

  it("não consulta quando a condição nasce inativa", () => {
    const tick = vi.fn();
    renderHook(() => usePolling(tick, false));

    act(() => vi.advanceTimersByTime(10 * POLL_INTERVAL_MS));
    expect(tick).not.toHaveBeenCalled();
  });

  it("para quando a condição de parada vira verdadeira e volta quando ela reativa", () => {
    const tick = vi.fn();
    const { rerender } = renderHook(({ active }) => usePolling(tick, active), {
      initialProps: { active: true },
    });
    act(() => vi.advanceTimersByTime(POLL_INTERVAL_MS));
    expect(tick).toHaveBeenCalledTimes(1);

    rerender({ active: false });
    act(() => vi.advanceTimersByTime(5 * POLL_INTERVAL_MS));
    expect(tick).toHaveBeenCalledTimes(1);

    rerender({ active: true });
    act(() => vi.advanceTimersByTime(POLL_INTERVAL_MS));
    expect(tick).toHaveBeenCalledTimes(2);
  });

  it("para ao desmontar", () => {
    const tick = vi.fn();
    const { unmount } = renderHook(() => usePolling(tick, true));
    act(() => vi.advanceTimersByTime(POLL_INTERVAL_MS));
    expect(tick).toHaveBeenCalledTimes(1);

    unmount();
    act(() => vi.advanceTimersByTime(5 * POLL_INTERVAL_MS));
    expect(tick).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("chama a função mais recente sem reiniciar o relógio a cada renderização", () => {
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = renderHook(({ tick }) => usePolling(tick, true), {
      initialProps: { tick: first },
    });
    act(() => vi.advanceTimersByTime(2000));

    rerender({ tick: second });
    act(() => vi.advanceTimersByTime(1000)); // 3 s since the start, not since the rerender

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });

  it("aceita outro intervalo", () => {
    const tick = vi.fn();
    renderHook(() => usePolling(tick, true, 500));

    act(() => vi.advanceTimersByTime(1500));
    expect(tick).toHaveBeenCalledTimes(3);
  });
});
