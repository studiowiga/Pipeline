// Captures PNG de la fenetre reelle de Pipeline (meme code que le plugin), pour l'apercu et la notice.
// Une corde pincee synthetique est jouee pour que la ligne d'info montre l'ecart de hauteur reel.
#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <random>
using namespace juce;

struct Pluck
{
    std::vector<float> d; int w = 0; float damp = 0.999f;
    void start (float fs, float hz, float amp)
    {
        d.assign ((size_t) std::lround (fs / hz - 0.5f), 0.0f);
        std::mt19937 r (3); std::uniform_real_distribution<float> u (-amp, amp);
        float prev = 0; for (auto& v : d) { prev += 0.5f * (u (r) - prev); v = prev; }
        damp = std::pow (0.001f, 1.0f / (6.0f * hz)); w = 0;
    }
    float tick()
    {
        if (d.empty()) return 0.0f;
        const int n = (int) d.size(); const float y = d[(size_t) w]; const int nx = (w + 1) % n;
        d[(size_t) w] = 0.5f * (y + d[(size_t) nx]) * damp; w = nx; return y;
    }
};

int main (int argc, char** argv)
{
    ScopedJuceInitialiser_GUI init;
    const String out = argc > 1 ? argv[1] : ".";
    PipelineAudioProcessor proc;
    proc.prepareToPlay (48000.0, 256);
    std::unique_ptr<AudioProcessorEditor> ed (proc.createEditor());
    auto* ped = static_cast<PipelineAudioProcessorEditor*> (ed.get());
    std::printf ("taille par defaut : %d x %d\n", ed->getWidth(), ed->getHeight());

    auto pump = [] (int n) { for (int i = 0; i < n; ++i) MessageManager::getInstance()->runDispatchLoopUntil (35); };
    auto play = [&] (float hz, float seconds, float amp = 0.35f)
    {
        Pluck s; s.start (48000.0f, hz, amp);
        const int blocks = (int) (seconds * 48000.0f / 256.0f);
        for (int b = 0; b < blocks; ++b)
        {
            AudioBuffer<float> buf (2, 256); MidiBuffer m;
            for (int i = 0; i < 256; ++i) { const float v = s.tick(); buf.setSample (0, i, v); buf.setSample (1, i, v); }
            proc.processBlock (buf, m);
            if (b % 6 == 0) pump (1);
        }
    };
    auto save = [&] (const String& name)
    {
        auto img = ed->createComponentSnapshot (ed->getLocalBounds(), true, 2.0f);
        File f (out + "/" + name + ".png"); f.deleteFile();
        FileOutputStream os (f); PNGImageFormat().writeImageToStream (img, os);
        std::printf ("%s (%d x %d) cents %.1f\n", f.getFullPathName().toRawUTF8(), img.getWidth(), img.getHeight(), proc.shownCents.load());
    };
    auto shot = [&] (const String& name, int preset, bool active, float hz, float seconds, int height, const char* touch = nullptr, float touchTo = 0.0f)
    {
        ped->setScaledHeight (height);
        proc.applyFactoryPreset (preset);
        proc.setParamValue ("active", active ? 1.f : 0.f);
        pump (20);
        if (hz > 0) play (hz, seconds);
        if (touch != nullptr) proc.setParamValue (touch, touchTo);
        pump (14);
        save (name);
    };
    shot ("pipeline_default", 0, true,  0.0f,   0.0f, PipelineAudioProcessorEditor::defaultH);
    shot ("pipeline_full",    0, true,  196.0f, 1.2f, PipelineAudioProcessorEditor::baseH);
    shot ("pipeline_envp",    12, true, 110.0f, 0.15f, PipelineAudioProcessorEditor::baseH);
    shot ("pipeline_status",  6, true,  0.0f,   0.0f, PipelineAudioProcessorEditor::baseH, "rate", 7.2f);
    shot ("pipeline_mix",     13, true, 0.0f,   0.0f, PipelineAudioProcessorEditor::baseH, "depth", 5.0f);
    shot ("pipeline_bypass",  9, false, 0.0f,   0.0f, PipelineAudioProcessorEditor::baseH);
    proc.setParamValue ("sync", 1.0f);
    shot ("pipeline_sync",    2, true,  0.0f,   0.0f, PipelineAudioProcessorEditor::baseH, "rate", 6.6f);
    proc.setParamValue ("sync", 0.0f);

    // footswitch : Flexi-Switch (appui maintenu > 0,45 s alors que l'effet etait coupe = momentane)
    {
        proc.applyFactoryPreset (0);
        proc.setParamValue ("active", 0.0f);
        pump (10);
        Component* fsComp = nullptr;
        for (auto* c : ed->getChildren()) if (dynamic_cast<FootSwitchArea*> (c) != nullptr) fsComp = c;
        const auto pt = fsComp->getLocalBounds().getCentre().toFloat();
        auto src = Desktop::getInstance().getMainMouseSource();
        MouseEvent ev (src, pt, ModifierKeys (ModifierKeys::leftButtonModifier), 1.0f, 0, 0, 0, 0, fsComp, fsComp, Time::getCurrentTime(), pt, Time::getCurrentTime(), 1, false);
        fsComp->mouseDown (ev);
        play (196.0f, 0.6f);
        pump (8);
        save ("pipeline_pressed");
        const bool onWhileHeld = proc.raw ("active") > 0.5f;
        fsComp->mouseUp (ev.withNewPosition (pt));
        pump (3);
        std::printf ("Flexi-Switch : maintenu -> %s, relache -> %s\n", onWhileHeld ? "ON" : "OFF", proc.raw ("active") > 0.5f ? "ON (ERREUR)" : "OFF");
        // appui bref : bascule (reste allume)
        fsComp->mouseDown (ev); fsComp->mouseUp (ev.withNewPosition (pt)); pump (3);
        std::printf ("Flexi-Switch : appui bref -> %s\n", proc.raw ("active") > 0.5f ? "ON" : "OFF (ERREUR)");
    }

    // pedale d'expression : course 2..116 sur CC 20 (rate)
    {
        auto sendCC = [&] (int cc, int v)
        {
            AudioBuffer<float> b (2, 256); b.clear(); MidiBuffer m; m.addEvent (MidiMessage::controllerEvent (1, cc, v), 0);
            proc.processBlock (b, m);
            for (int k = 0; k < 20; ++k) { MidiBuffer e; b.clear(); proc.processBlock (b, e); }
            pump (3);
        };
        sendCC (20, 2);   const float a = proc.raw ("rate");
        sendCC (20, 116); const float c = proc.raw ("rate");
        sendCC (20, 59);  const float mid = proc.raw ("rate");
        std::printf ("pedale 2..116 -> rate %.2f / %.2f, mi-course %.2f\n", a, c, mid);
        sendCC (22, 127); std::printf ("CC 22 = 127 -> mode %d (attendu 7)\n", (int) proc.raw ("mode"));
        sendCC (22, 0);   std::printf ("CC 22 = 0   -> mode %d (attendu 0)\n", (int) proc.raw ("mode"));
        // footswitch MIDI momentane (127 a l'appui, 0 au relachement) : chaque appui bascule, sans maintenir
        proc.setParamValue ("active", 0.0f); pump (3);
        sendCC (24, 127); sendCC (24, 0); const bool on1 = proc.raw ("active") > 0.5f;
        sendCC (24, 127); sendCC (24, 0); const bool on2 = proc.raw ("active") > 0.5f;
        std::printf ("footswitch MIDI : 1er appui -> %s, 2e appui -> %s (attendu ON puis OFF)\n", on1 ? "ON" : "OFF", on2 ? "ON" : "OFF");
    }
    ed.reset();
    return 0;
}
