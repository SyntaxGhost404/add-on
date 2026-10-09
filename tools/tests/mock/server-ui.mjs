// Minimal stand-in for @minecraft/server-ui. A form "shows" by taking the next scripted response
// from player.formResponses (a button index, or undefined to close the form).
export const FormCancelationReason = { UserBusy: "UserBusy", UserClosed: "UserClosed" };

export class ActionFormData {
  constructor() {
    this.data = { title: "", body: "", buttons: [] };
  }
  title(t) {
    this.data.title = String(t);
    return this;
  }
  body(t) {
    this.data.body = String(t);
    return this;
  }
  button(text, icon) {
    this.data.buttons.push({ text: String(text), icon });
    return this;
  }
  label() {
    return this;
  }
  header() {
    return this;
  }
  divider() {
    return this;
  }
  async show(player) {
    player.formsShown.push(this.data);
    const sel = player.formResponses.shift();
    if (sel === undefined) return { canceled: true, cancelationReason: FormCancelationReason.UserClosed };
    if (sel < 0 || sel >= this.data.buttons.length) throw new Error(`mock form: no button ${sel} in "${this.data.title}"`);
    return { canceled: false, selection: sel };
  }
}
