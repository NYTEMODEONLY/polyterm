import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

function monitorRuntime(page) {
  const errors = [];
  page.on("pageerror", error => errors.push(`page: ${error.message}`));
  page.on("console", message => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  return errors;
}

async function loadGame(page, graphics = "2d") {
  await page.addInitScript(mode => {
    localStorage.clear();
    localStorage.setItem("balkan-civ-gfx", mode);
    localStorage.setItem("balkan-civ-reduce-motion", "1");
    localStorage.setItem("balkan-civ-tips-off", "1");
  }, graphics);
  await page.goto("/index.html");
  await expect(page.locator("#start-screen")).toBeVisible();
  await page.locator("#sel-mapsize").selectOption("small");
  await page.locator("#sel-opponents").selectOption("3");
  await page.locator("#chk-barbs").uncheck();
  await page.locator("#btn-start").click();
  await expect(page.locator("#start-screen")).toBeHidden();
  await expect(page.locator("#map")).toBeVisible();
  await expect.poll(() => page.evaluate(() => !!(UI.game && UI.renderer))).toBe(true);
  await expect.poll(() => page.locator("#map").evaluate(canvas => canvas.width > 300 && canvas.height > 300)).toBe(true);
}

async function expectFocusInside(page, selector) {
  await expect.poll(() => page.evaluate(sel => {
    const root = document.querySelector(sel);
    return !!(root && root.contains(document.activeElement));
  }, selector)).toBe(true);
}

async function expectNoAxeViolations(page, selector) {
  const result = await new AxeBuilder({ page }).include(selector).analyze();
  expect(result.violations.map(violation => ({
    id: violation.id,
    impact: violation.impact,
    targets: violation.nodes.map(node => node.target.join(" ")),
  }))).toEqual([]);
}

async function expectNoViewportOverflow(page) {
  const overflow = await page.evaluate(() => {
    const offenders = [...document.body.querySelectorAll("*")].filter(element => {
      if (!element.getClientRects().length || getComputedStyle(element).visibility === "hidden") return false;
      if (element.getAnimations().some(animation => animation.playState === "running")) return false;
      let parent = element.parentElement;
      while (parent && parent !== document.body) {
        const overflowX = getComputedStyle(parent).overflowX;
        if (overflowX === "auto" || overflowX === "scroll" || overflowX === "hidden") return false;
        parent = parent.parentElement;
      }
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && (rect.left < -1 || rect.right > window.innerWidth + 1);
    }).map(element => ({ id: element.id, className: element.className, tag: element.tagName,
      left: Math.round(element.getBoundingClientRect().left), right: Math.round(element.getBoundingClientRect().right) }));
    return { document: document.documentElement.scrollWidth - window.innerWidth, offenders: offenders.slice(0, 12) };
  });
  expect(overflow).toEqual({ document: 0, offenders: [] });
}

async function canvasPixelStats(page, graphics) {
  return page.evaluate(mode => {
    const renderer = UI.renderer, canvas = renderer.canvas;
    renderer.dirty = true;
    renderer.draw(UI.game);
    const size = 112;
    let pixels;
    if (mode === "3d") {
      const gl = renderer.three.getContext();
      gl.finish();
      pixels = new Uint8Array(size * size * 4);
      gl.readPixels(Math.max(0, Math.floor(gl.drawingBufferWidth / 2 - size / 2)),
        Math.max(0, Math.floor(gl.drawingBufferHeight / 2 - size / 2)), size, size,
        gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    } else {
      const ctx = canvas.getContext("2d");
      pixels = ctx.getImageData(Math.max(0, Math.floor(canvas.width / 2 - size / 2)),
        Math.max(0, Math.floor(canvas.height / 2 - size / 2)), size, size).data;
    }
    const colors = new Set();
    let opaque = 0, min = 255, max = 0;
    for (let i = 0; i < pixels.length; i += 4) {
      if (pixels[i + 3] > 0) opaque++;
      const light = Math.max(pixels[i], pixels[i + 1], pixels[i + 2]);
      min = Math.min(min, light); max = Math.max(max, light);
      colors.add(`${pixels[i] >> 4}:${pixels[i + 1] >> 4}:${pixels[i + 2] >> 4}:${pixels[i + 3] >> 6}`);
    }
    return { colors: colors.size, opaque, range: max - min, three: !!renderer.three,
      width: canvas.width, height: canvas.height };
  }, graphics);
}

test("launch selection and campaign dialogs are keyboard and screen-reader complete", async ({ page }) => {
  const errors = monitorRuntime(page);
  await page.addInitScript(() => localStorage.clear());
  await page.goto("/index.html");

  const selectors = page.locator(".civ-select");
  await expect(selectors).toHaveCount(9);
  await expect(selectors.first()).toHaveAttribute("aria-pressed", "true");
  await selectors.nth(1).focus();
  await page.keyboard.press("Enter");
  await expect(selectors.nth(1)).toHaveAttribute("aria-pressed", "true");
  await expect(selectors.first()).toHaveAttribute("aria-pressed", "false");

  await page.locator("#btn-campaign").click();
  const campaign = page.getByRole("dialog", { name: /Campaign/ });
  await expect(campaign).toBeVisible();
  await expect(campaign).toHaveAttribute("aria-modal", "true");
  await expect(page.locator("#start-screen")).toHaveJSProperty("inert", true);
  await expectFocusInside(page, "#campaign-modal");
  for (let i = 0; i < 14; i++) {
    await page.keyboard.press("Tab");
    await expectFocusInside(page, "#campaign-modal");
  }
  await expectNoAxeViolations(page, "#campaign-modal");
  await page.keyboard.press("Escape");
  await expect(campaign).toBeHidden();
  await expect(page.locator("#btn-campaign")).toBeFocused();
  await expectNoAxeViolations(page, "#start-screen");
  await expectNoViewportOverflow(page);
  expect(errors).toEqual([]);
});

test("event decisions trap focus without blocking keyboard choices or leaking turn shortcuts", async ({ page }, testInfo) => {
  const errors = monitorRuntime(page);
  await loadGame(page, "2d");
  const pixels = await canvasPixelStats(page, "2d");
  expect(pixels).toMatchObject({ three: false });
  expect(pixels.colors).toBeGreaterThan(8);
  expect(pixels.opaque).toBeGreaterThan(10_000);
  expect(pixels.range).toBeGreaterThan(30);
  await expectNoAxeViolations(page, "#game-ui");

  const before = await page.evaluate(() => {
    const game = UI.game, player = game.players[game.viewer];
    game.pendingEvents = [{ id: "browser:event", player: game.viewer, key: "FESTIVAL",
      cityId: null, turn: game.turn }];
    return { turn: game.turn, moodTurns: player.moodTurns, moodDelta: player.moodDelta };
  });
  await page.locator("#btn-endturn").focus();
  await page.keyboard.press("Enter");
  const event = page.getByRole("dialog", { name: /Spontaneous Festival/ });
  await expect(event).toBeVisible();
  await expect(page.locator("#game-ui")).toHaveJSProperty("inert", true);
  await expectFocusInside(page, "#event-modal");

  await page.keyboard.press("Escape");
  await expect(event).toBeVisible();
  for (let i = 0; i < 7; i++) {
    await page.keyboard.press("Tab");
    await expectFocusInside(page, "#event-modal");
  }
  await expectNoAxeViolations(page, "#event-modal");

  const choices = page.locator("#event-modal .event-choice:not([disabled])");
  if (testInfo.project.name === "chromium-mobile") {
    const boxes = await choices.evaluateAll(nodes => nodes.map(node => {
      const rect = node.getBoundingClientRect();
      return { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width) };
    }));
    expect(boxes[1].y).toBeGreaterThan(boxes[0].y);
    expect(boxes[0].width).toBe(boxes[1].width);
  }
  await choices.first().focus();
  await page.keyboard.press("Enter");
  await expect(event).toBeHidden();
  await expect(page.locator("#btn-endturn")).toBeFocused();
  const after = await page.evaluate(() => ({ turn: UI.game.turn,
    moodTurns: UI.game.players[UI.game.viewer].moodTurns,
    moodDelta: UI.game.players[UI.game.viewer].moodDelta, pending: UI.game.pendingEvents.length }));
  expect(after).toEqual({ turn: before.turn, moodTurns: 8, moodDelta: 3, pending: 0 });

  await expectNoViewportOverflow(page);
  expect(errors).toEqual([]);
});

test("the 3D renderer produces a nonblank frame and responds to camera controls", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-desktop", "3D pixel contract runs once on desktop Chromium");
  const errors = monitorRuntime(page);
  await loadGame(page, "3d");
  await expect.poll(() => page.evaluate(() => !!UI.renderer.three)).toBe(true);
  const pixels = await canvasPixelStats(page, "3d");
  expect(pixels.three).toBe(true);
  expect(pixels.colors).toBeGreaterThan(8);
  expect(pixels.opaque).toBeGreaterThan(10_000);
  expect(pixels.range).toBeGreaterThan(30);

  const before = await page.evaluate(() => UI.renderer.cam.rot || 0);
  await page.locator("#btn-rot-right").click();
  await expect.poll(() => page.evaluate(() => UI.renderer.cam.rot || 0)).not.toBe(before);
  await expect(page.getByRole("img", { name: "Interactive world map" })).toBeVisible();
  await expectNoViewportOverflow(page);
  expect(errors).toEqual([]);
});
