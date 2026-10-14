// Minimal stand-in for @minecraft/server-ui 2.x. A form "shows" by taking the next scripted answer
// from player.answers:
//   number        ActionFormData: the button index
//   array         ModalFormData: values for the input controls, in order
//   "close"       the player closes the form
//   "busy"        the game cancels the form because the player is busy (the form is shown again)
//   function      called with (form, player) before answering; returns one of the above
export const FormCancelationReason = { UserBusy: "UserBusy", UserClosed: "UserClosed" };

function text(t) {
  if (typeof t === "string") return t;
  return JSON.stringify(t);
}

class Form {
  constructor(kind) {
    this.kind = kind;
    this.data = { kind, title: "", body: "", buttons: [], controls: [], submit: undefined };
  }
  title(t) {
    this.data.title = text(t);
    return this;
  }
  label(t) {
    this.data.controls.push({ type: "label", text: text(t) });
    return this;
  }
  header(t) {
    this.data.controls.push({ type: "header", text: text(t) });
    return this;
  }
  divider() {
    this.data.controls.push({ type: "divider" });
    return this;
  }
  async show(player) {
    let answer = player.answers.shift();
    if (typeof answer === "function") answer = answer(this.data, player);
    player.formsShown.push(this.data);
    if (answer === undefined) throw new Error(`mock: no scripted answer for form "${this.data.title}"`);
    if (answer === "close") return { canceled: true, cancelationReason: FormCancelationReason.UserClosed };
    if (answer === "busy") return { canceled: true, cancelationReason: FormCancelationReason.UserBusy };
    return this.answer(answer);
  }
}

export class ActionFormData extends Form {
  constructor() {
    super("action");
  }
  body(t) {
    this.data.body = text(t);
    return this;
  }
  button(t, icon) {
    if (icon !== undefined && typeof icon !== "string") throw new TypeError("button icon must be a string");
    this.data.buttons.push({ text: text(t), icon });
    return this;
  }
  answer(sel) {
    if (typeof sel !== "number" || sel < 0 || sel >= this.data.buttons.length) {
      throw new Error(`mock: no button ${sel} in "${this.data.title}" (${this.data.buttons.length} buttons)`);
    }
    return { canceled: false, selection: sel };
  }
}

export class ModalFormData extends Form {
  constructor() {
    super("modal");
    this.placeholders = ModalFormData.placeholders;
  }
  slider(label, min, max, options = {}) {
    if (arguments.length > 4 || (options !== undefined && typeof options !== "object")) {
      throw new TypeError("slider(label, min, max, options?) takes an options object in server-ui 2.x");
    }
    const step = options.valueStep ?? 1;
    const value = options.defaultValue ?? min;
    if (!(min < max)) throw new Error(`mock: slider "${text(label)}" has min ${min} >= max ${max}`);
    if (value < min || value > max) throw new Error(`mock: slider default ${value} outside ${min}..${max}`);
    this.data.controls.push({ type: "slider", text: text(label), min, max, step, value });
    return this;
  }
  toggle(label, options = {}) {
    this.data.controls.push({ type: "toggle", text: text(label), value: options.defaultValue ?? false });
    return this;
  }
  submitButton(t) {
    this.data.submit = text(t);
    return this;
  }
  answer(values) {
    const inputs = this.data.controls.filter((c) => c.type === "slider" || c.type === "toggle");
    if (!Array.isArray(values) || values.length !== inputs.length) {
      throw new Error(`mock: "${this.data.title}" has ${inputs.length} inputs, answer gave ${JSON.stringify(values)}`);
    }
    inputs.forEach((c, i) => {
      const v = values[i] === null ? c.value : values[i];
      if (c.type === "slider" && (v < c.min || v > c.max)) throw new Error(`mock: value ${v} outside slider ${c.min}..${c.max}`);
      c.answer = v;
    });
    // The game may or may not report a placeholder for labels, headers and dividers.
    const formValues = this.placeholders
      ? this.data.controls.map((c) => ("answer" in c ? c.answer : undefined))
      : inputs.map((c) => c.answer);
    return { canceled: false, formValues };
  }
}
ModalFormData.placeholders = true;
